"""The one small adapter between a cluster file and ``initialize()``.

The compiler prototype kept cluster loading outside the startup lifecycle on
purpose — ``initialize(cluster: Cluster)`` takes the object — because the
handoff format from the Evals track was not yet fixed. This module is that
adapter: a JSON document in, an ``aisafepy.adapt.Cluster`` out. It defines no
parallel types; every field is ``FailureRecord``'s own.

Format (``cluster_to_dict`` writes it, ``cluster_from_dict`` reads it)::

    {
      "label": 42,
      "summary": "cluster of 12 failures; common phrases: ...",
      "records": [
        {
          "id": "C-01/treatment/003",
          "input": "...the text the agent saw...",
          "output": "...what the agent did...",
          "was_violation": true,
          "attack_category": "injected_log_entry",      # optional, as are the rest
          "severity": "high",
          "scorer": "welfareguard.scorer",
          "score": 1.0,
          "metadata": {"harm_class": ["AW-1", "AW-3"], "arm": "treatment"},
          "timestamp": 1760000000.0,
          "source": "inspect"
        }
      ]
    }

Loading is strict: an unknown key, a missing required key, or a wrong type is a
``ValueError`` naming the record, never a silently dropped field. A format
drift in the handoff should break here, loudly, not compile into a guard that
quietly saw half the data.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from aisafepy.adapt import Cluster, FailureRecord

_RECORD_FIELDS = {f.name for f in dataclasses.fields(FailureRecord)}
_RECORD_REQUIRED = {
    f.name
    for f in dataclasses.fields(FailureRecord)
    if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
}
_CLUSTER_KEYS = {"label", "summary", "records"}


def record_from_dict(data: dict[str, Any], *, where: str = "record") -> FailureRecord:
    """Build a ``FailureRecord`` from a dict, refusing unknown or missing keys."""
    if not isinstance(data, dict):
        raise ValueError(f"{where}: expected an object, got {type(data).__name__}")
    unknown = set(data) - _RECORD_FIELDS
    if unknown:
        raise ValueError(f"{where}: unknown FailureRecord field(s) {sorted(unknown)}")
    missing = _RECORD_REQUIRED - set(data)
    if missing:
        raise ValueError(f"{where}: missing required field(s) {sorted(missing)}")
    if not isinstance(data["was_violation"], bool):
        raise ValueError(f"{where}: was_violation must be a boolean")
    for key in ("id", "input", "output"):
        if not isinstance(data[key], str):
            raise ValueError(f"{where}: {key} must be a string")
    return FailureRecord(**data)


def cluster_from_dict(data: dict[str, Any]) -> Cluster:
    """Build a ``Cluster`` from a dict in the documented format."""
    if not isinstance(data, dict):
        raise ValueError(f"cluster: expected an object, got {type(data).__name__}")
    unknown = set(data) - _CLUSTER_KEYS
    if unknown:
        raise ValueError(f"cluster: unknown key(s) {sorted(unknown)}")
    missing = {"label", "records"} - set(data)
    if missing:
        raise ValueError(f"cluster: missing required key(s) {sorted(missing)}")
    if not isinstance(data["label"], int) or isinstance(data["label"], bool):
        raise ValueError("cluster: label must be an integer")
    if not isinstance(data["records"], list):
        raise ValueError("cluster: records must be a list")
    records = [record_from_dict(r, where=f"records[{i}]") for i, r in enumerate(data["records"])]
    return Cluster(label=data["label"], records=records, summary=str(data.get("summary", "")))


def cluster_to_dict(cluster: Cluster) -> dict[str, Any]:
    """Serialise a ``Cluster`` to the documented format. ``centroid`` is dropped."""
    return {
        "label": cluster.label,
        "summary": cluster.summary,
        "records": [dataclasses.asdict(r) for r in cluster.records],
    }


def load_cluster(path: str | Path) -> Cluster:
    """Read a cluster JSON file. See the module docstring for the format."""
    with Path(path).open(encoding="utf-8") as fh:
        return cluster_from_dict(json.load(fh))


def save_cluster(cluster: Cluster, path: str | Path) -> None:
    """Write a cluster JSON file in the documented format."""
    with Path(path).open("w", encoding="utf-8") as fh:
        json.dump(cluster_to_dict(cluster), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
