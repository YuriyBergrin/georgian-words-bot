from dataclasses import dataclass


@dataclass(slots=True)
class ImportWordsResult:
    added: int
    updated: int
    skipped: int
    errors_count: int
    errors: list[str]


@dataclass(slots=True)
class SearchWordsPage:
    total: int
    rows: list[tuple[str, str, str | None]]


@dataclass(slots=True)
class EditWordContext:
    exists: bool
    current_topic: str | None
