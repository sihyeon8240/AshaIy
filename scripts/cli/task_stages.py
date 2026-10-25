"""Run ordered repository stages without retaining success across invocations."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    name: str
    run: Callable[[], int]


@dataclass(frozen=True)
class StageResult:
    completed: tuple[str, ...]
    failed: str | None
    returncode: int


def run_stages(stages: Iterable[Stage]) -> StageResult:
    completed = []
    for stage in stages:
        status = stage.run()
        if status:
            return StageResult(tuple(completed), stage.name, status)
        completed.append(stage.name)
    return StageResult(tuple(completed), None, 0)
