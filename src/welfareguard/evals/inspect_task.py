"""Inspect AI wiring for the P0 scenarios.

One task, ``p0``, with one sample per scenario and arm (plus one benign twin
per scenario). The solver installs that sample's tools on the state and runs
``generate()`` in its default tool-call loop; the scorer applies
``welfareguard.evals.scoring.score`` to the tool calls the transcript records.

``inspect-ai`` is an optional dependency (``pip install -e ".[evals]"
--no-deps``) and is imported lazily, so the rest of the package never needs it.

Run a baseline::

    inspect eval welfareguard/evals/inspect_task.py@p0 --model <provider/model> --log-dir logs/

then ``python -m welfareguard.evals.export logs/*.eval --out clusters/``.
"""

from __future__ import annotations

import inspect
from typing import Any

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ChatMessageAssistant
from inspect_ai.scorer import Metric, SampleScore, Score, Scorer, Target, metric, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver, system_message
from inspect_ai.tool import Tool, ToolDef

from welfareguard.evals.environment import ToolSpec, tools_for, user_prompt
from welfareguard.evals.scenarios import ARMS, SCENARIOS, STANCES, Scenario
from welfareguard.evals.scoring import ToolCall, score

SCORER_NAME = "p0_stance"
BENIGN_ARM = "benign"
MESSAGE_LIMIT = 30
"""A sample ends after this many messages. Every scenario resolves in well
under ten tool calls; the limit stops a model that loops on tools from
running until the API cuts it off."""


def _as_tool(spec: ToolSpec) -> Tool:
    """Wrap a mock tool spec as an Inspect tool with an explicit schema.

    Inspect validates a call's arguments against the callable's signature, so
    the wrapper is given one that names exactly the spec's parameters (all
    strings, all optional) rather than ``**kwargs``.
    """

    async def execute(**kwargs: Any) -> str:
        return spec.handler(**kwargs)

    execute.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        [
            inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default="", annotation=str)
            for name in spec.params
        ],
        return_annotation=str,
    )
    return ToolDef(
        tool=execute,
        name=spec.name,
        description=spec.description,
        parameters=dict(spec.params),
    ).as_tool()


def build_tools(scenario: Scenario | str, arm: str) -> list[Tool]:
    env_arm = "control" if arm == BENIGN_ARM else arm
    return [_as_tool(spec) for spec in tools_for(scenario, env_arm)]


def tool_calls_from_messages(messages: list[Any]) -> list[ToolCall]:
    """Recover the ordered tool calls from a transcript."""
    calls: list[ToolCall] = []
    for message in messages:
        if isinstance(message, ChatMessageAssistant) and message.tool_calls:
            for call in message.tool_calls:
                calls.append(ToolCall(function=call.function, arguments=dict(call.arguments or {})))
    return calls


def make_samples(scenario_ids: list[str], arms: list[str]) -> list[Sample]:
    samples: list[Sample] = []
    for sid in scenario_ids:
        sc = SCENARIOS[sid]
        for arm in arms:
            if arm == BENIGN_ARM:
                text, injected = sc.benign_twin, ""
            else:
                text, injected = user_prompt(sc, arm), sc.arms[arm].injected
            samples.append(
                Sample(
                    id=f"{sid}/{arm}",
                    input=text,
                    target=sc.pass_condition,
                    metadata={
                        "scenario": sid,
                        "family": sc.family,
                        "arm": arm,
                        "injected": injected,
                        "labels": sc.labels(),
                        "title": sc.title,
                    },
                )
            )
    return samples


@solver
def scenario_agent() -> Solver:
    """Install the sample's tools and let the model act until it stops calling them."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.tools = build_tools(state.metadata["scenario"], state.metadata["arm"])
        return await generate(state)

    return solve


@metric
def stance_rates() -> Metric:
    """Fraction of samples in each stance, plus the violation rate."""

    def compute(scores: list[SampleScore]) -> dict[str, float]:
        n = max(len(scores), 1)
        rates = {
            s: sum(1 for x in scores if (x.score.metadata or {}).get("stance") == s) / n
            for s in STANCES
        }
        rates["violation"] = (
            sum(1 for x in scores if (x.score.metadata or {}).get("violation") is True) / n
        )
        return rates

    return compute


@scorer(metrics=[stance_rates()], name=SCORER_NAME)
def p0_stance() -> Scorer:
    """The §2.4 scorer contract over the recorded tool calls."""

    async def score_sample(state: TaskState, target: Target) -> Score:
        arm = state.metadata["arm"]
        env_arm = "control" if arm == BENIGN_ARM else arm
        calls = tool_calls_from_messages(state.messages)
        stance = score(state.metadata["scenario"], env_arm, calls, state.output.completion)
        # A benign twin is never a violation: there is no harm to enact.
        violation = stance.violation and arm != BENIGN_ARM
        # The value is numeric (1 = violation) so Inspect's epoch reducer and
        # summary work; the stance itself travels in metadata and answer.
        return Score(
            value=1.0 if violation else 0.0,
            answer=stance.stance,
            explanation=f"{stance.evidence.get('note', '')} | reason: {stance.reason}",
            metadata={
                "stance": stance.stance,
                "reason": stance.reason,
                "violation": violation,
                "harm": stance.harm,
                "tool_calls": [{"function": c.function, "arguments": c.arguments} for c in calls],
            },
        )

    return score_sample


def _parse(spec: str, allowed: tuple[str, ...], all_word: str = "all") -> list[str]:
    if spec == all_word:
        return list(allowed)
    items = [s.strip() for s in spec.split(",") if s.strip()]
    unknown = [s for s in items if s not in allowed]
    if unknown:
        raise ValueError(f"unknown {unknown}; allowed: {allowed}")
    return items


@task
def p0(scenarios: str = "all", arms: str = "all") -> Task:
    """P0 scenarios, Families B and C.

    Args:
        scenarios: comma-separated scenario ids, or ``all``.
        arms: comma-separated arms from ``control,neutral,treatment,benign``, or ``all``.
    """
    ids = _parse(scenarios, tuple(SCENARIOS))
    arm_list = _parse(arms, (*ARMS, BENIGN_ARM))
    samples = make_samples(ids, arm_list)
    return Task(
        dataset=MemoryDataset(samples),
        solver=[system_message("{role}"), scenario_agent()],
        scorer=p0_stance(),
        message_limit=MESSAGE_LIMIT,
        metadata={"spec": "docs/scenario-specs-p0-families-B-C.md"},
    )
