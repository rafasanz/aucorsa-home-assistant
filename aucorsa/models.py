from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PageContext:
    nonce: str
    post_id: str


@dataclass(frozen=True)
class LineMatch:
    id: str
    line: str
    label: str
    route: Optional[str]


@dataclass(frozen=True)
class StopMatch:
    id: str
    label: str
    link: Optional[str]


@dataclass(frozen=True)
class LineEstimation:
    line: str
    internal_line_id: Optional[str]
    route: Optional[str]
    line_color: Optional[str]
    next_bus_min: Optional[int]
    following_bus_min: Optional[int]


@dataclass(frozen=True)
class StopEstimationsResult:
    stop_id: str
    stop_label: Optional[str]
    lines: list[LineEstimation] = field(default_factory=list)


@dataclass(frozen=True)
class EstimationResult:
    stop_id: str
    line: str
    internal_line_id: str
    stop_label: Optional[str]
    route: Optional[str]
    line_color: Optional[str]
    next_bus_min: Optional[int]
    following_bus_min: Optional[int]
