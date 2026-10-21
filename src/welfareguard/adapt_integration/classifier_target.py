"""Tier-2 classifier target trained on real negatives.

aisafepy's ``_ClassifierTarget`` builds its negative set as the positives
spelled backwards (``classifier.py``, "silly negatives"). A classifier trained
that way learns "forward English is unsafe" and blocks every request; the
first real run measured a 100% false-positive rate on the benign twins. Its
own docstring calls the loop a stub and invites subclassing, which is what
this is. aisafepy is not modified; this class overrides ``compile_for_cluster``
and supplies its own fit.

Negatives come from two places, both real:

* the cluster's own non-violating records (control, neutral and treatment
  arms on which the agent did not comply), and
* ``extra_negatives`` passed in by the caller, meant for the benign twins.
  The caller decides the split; the benchmark CLI trains on half the twins
  and measures false positives on the other half, so the measurement is
  never against text the model trained on.

The artifact shape matches upstream exactly (``kind="classifier"``,
``payload`` = checkpoint directory, ``payload=None`` with ``metadata["reason"]``
when skipped or deferred), so ``CompiledGuardSet``, the cascade and the
runtime need no change.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from aisafepy.adapt import Cluster, CompiledArtifact
from aisafepy.adapt.compile.classifier import _ClassifierTarget

MIN_POSITIVES = 8
"""Upstream's threshold; kept so "skipped" means the same thing in both."""


@dataclass
class WelfareClassifierTarget(_ClassifierTarget):
    """``_ClassifierTarget`` with real negatives and a balanced training set."""

    extra_negatives: tuple[str, ...] = ()
    seed: int = 0

    def compile_for_cluster(self, cluster: Cluster) -> CompiledArtifact:
        positive_records = [r for r in cluster.records if r.was_violation]
        negatives = [r.input for r in cluster.records if not r.was_violation]
        negatives += list(self.extra_negatives)
        # The threshold counts records, as upstream does. Training uses unique
        # texts: the same injected string recurs across epochs, and repeating
        # it adds nothing the balancing step does not already do.
        positives = list(dict.fromkeys(r.input for r in positive_records))
        negatives = list(dict.fromkeys(negatives))

        common = {
            "kind": self.kind,
            "cluster_label": cluster.label,
            "attack_success_rate": cluster.attack_success_rate,
            "n_records": cluster.size,
            "summary": cluster.summary,
        }
        if len(positive_records) < MIN_POSITIVES:
            return CompiledArtifact(
                name=f"classifier-skipped-{cluster.label}",
                payload=None,
                metadata={
                    "reason": "too few positives for distillation",
                    "n_positives": len(positive_records),
                    "n_negatives": len(negatives),
                },
                **common,
            )
        if not negatives:
            # Non-fatal, like upstream's own skipped outcome: the regex tier is a
            # valid v1 deployment on its own. A classifier trained without real
            # negatives cannot be measured, so none is produced.
            return CompiledArtifact(
                name=f"classifier-skipped-{cluster.label}",
                payload=None,
                metadata={
                    "reason": "no negatives: pass the benign set as extra_negatives or include non-violating records",
                    "n_positives": len(positive_records),
                    "n_negatives": 0,
                },
                **common,
            )

        out_path = Path(self.out or f"guards/classifier_cluster_{cluster.label}.pt")
        spec = {
            "base": self.base,
            "out": str(out_path),
            "epochs": self.epochs,
            "n_positives": len(positive_records),
            "n_unique_positive_texts": len(positives),
            "n_negatives": len(negatives),
            "negatives": "cluster non-violations + extra_negatives (real text, not reversed)",
        }
        try:
            artifact_path = _fit(
                base=self.base,
                positives=positives,
                negatives=negatives,
                epochs=self.epochs,
                out=out_path,
                seed=self.seed,
            )
        except ModuleNotFoundError as exc:
            if exc.name not in ("torch", "transformers"):
                # A missing optional dependency inside a present torch stack is
                # a real failure, not the documented deferred outcome.
                raise
            return CompiledArtifact(
                name=f"classifier-deferred-{cluster.label}",
                payload=None,
                metadata={"deferred": True, "reason": str(exc), "training_spec": spec},
                **common,
            )
        return CompiledArtifact(
            name=f"distilled-{cluster.label}",
            payload=str(artifact_path),
            metadata=spec,
            **common,
        )


def _fit(
    *,
    base: str,
    positives: list[str],
    negatives: list[str],
    epochs: int,
    out: Path,
    seed: int,
) -> Path:
    """Fine-tune a small encoder on real positives and negatives.

    Same recipe as upstream (AdamW, lr 5e-5, truncation at 256 tokens) with
    two differences: the negatives are real text, and the set is balanced by
    oversampling the smaller class and shuffled each epoch.
    """
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - depends on env
        raise ModuleNotFoundError(
            "Classifier distillation requires torch and transformers "
            '(pip install -e ".[classifier]" --no-deps after the CPU torch index).',
            name=exc.name or "torch",
        ) from exc

    rng = random.Random(seed)
    torch.manual_seed(seed)
    n = max(len(positives), len(negatives))
    examples = [(t, 1) for t in positives] + [(t, 0) for t in negatives]
    examples += [(rng.choice(positives), 1) for _ in range(n - len(positives))]
    examples += [(rng.choice(negatives), 0) for _ in range(n - len(negatives))]

    tokenizer = AutoTokenizer.from_pretrained(base)
    model = AutoModelForSequenceClassification.from_pretrained(base, num_labels=2)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5)
    for _ in range(epochs):
        rng.shuffle(examples)
        for text, label in examples:
            enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=256).to(device)
            loss = model(**enc, labels=torch.tensor([label], device=device)).loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

    target = out.parent / out.stem
    target.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(target)
    tokenizer.save_pretrained(target)
    return target
