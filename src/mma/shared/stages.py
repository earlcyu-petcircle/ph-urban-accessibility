"""The marker a stage raises until it is built, so the CLI can say which PR brings it."""

from __future__ import annotations


class StageNotBuilt(NotImplementedError):
    def __init__(self, number: int, name: str, pr: int) -> None:
        self.number = number
        self.name = name
        self.pr = pr
        super().__init__(f"stage {number} ({name}) is not built yet: it arrives in PR {pr}")
