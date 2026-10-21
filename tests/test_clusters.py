"""Shape assertions for the cluster handoff adapter.

The fixture data is the structural cluster from ``conftest`` — spans the
scaffold already contains — so no scenario data is authored here.
"""

from __future__ import annotations

import dataclasses
import json

import pytest
from aisafepy.adapt import Cluster, FailureRecord

from conftest import make_cluster
from welfareguard import clusters, compiler


def test_round_trip_preserves_every_record_field():
    """Drift guarded: a ``FailureRecord`` field silently dropped on the way through."""
    cluster = make_cluster()
    # FailureRecord is frozen; populate the optional fields on a copy.
    cluster.records[0] = dataclasses.replace(
        cluster.records[0],
        attack_category="injected_log_entry",
        metadata={"harm_class": ["AW-1"], "arm": "treatment"},
    )

    loaded = clusters.cluster_from_dict(clusters.cluster_to_dict(cluster))

    assert isinstance(loaded, Cluster)
    assert loaded.label == cluster.label
    assert loaded.summary == cluster.summary
    assert loaded.records == cluster.records
    assert all(isinstance(r, FailureRecord) for r in loaded.records)


def test_loaded_cluster_compiles(tmp_path):
    """The adapter's output is a real ``Cluster``: the real compiler accepts it."""
    path = tmp_path / "cluster.json"
    clusters.save_cluster(make_cluster(label=7), path)

    guard_set = compiler.compile(clusters.load_cluster(path))
    assert guard_set.artifact_of_kind(compiler.REGEX_KIND).cluster_label == 7


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["records"][0].update({"harm_class": "AW-1"}), "unknown FailureRecord field"),
        (lambda d: d["records"][0].pop("was_violation"), "missing required field"),
        (lambda d: d["records"][0].update({"was_violation": "yes"}), "must be a boolean"),
        (lambda d: d.update({"centroid": [0.1]}), "unknown key"),
        (lambda d: d.pop("records"), "missing required key"),
        (lambda d: d.update({"label": "42"}), "label must be an integer"),
        (lambda d: d["records"][0].update({"metadata": None}), "metadata must be an object"),
        (lambda d: d["records"][0].update({"score": "1.0"}), "score must be a number"),
    ],
)
def test_format_drift_is_loud(mutate, message):
    """Drift guarded: a handoff-format change compiling a guard off half the data."""
    data = clusters.cluster_to_dict(make_cluster())
    mutate(data)
    with pytest.raises(ValueError, match=message):
        clusters.cluster_from_dict(data)


def test_file_format_is_plain_json(tmp_path):
    path = tmp_path / "c.json"
    clusters.save_cluster(make_cluster(n_records=2), path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"label", "summary", "records"}
    assert len(data["records"]) == 2
