from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._version import get_version

if TYPE_CHECKING:
    from .client import AucorsaClient
    from .models import EstimationResult, LineEstimation, LineMatch, StopEstimationsResult, StopMatch


__version__ = get_version()

__all__ = [
    "AucorsaClient",
    "EstimationResult",
    "LineEstimation",
    "LineMatch",
    "StopEstimationsResult",
    "StopMatch",
    "__version__",
]


def __getattr__(name: str) -> Any:
    if name == "AucorsaClient":
        from .client import AucorsaClient

        return AucorsaClient
    if name in {"EstimationResult", "LineEstimation", "LineMatch", "StopEstimationsResult", "StopMatch"}:
        from .models import (
            EstimationResult,
            LineEstimation,
            LineMatch,
            StopEstimationsResult,
            StopMatch,
        )

        exports = {
            "EstimationResult": EstimationResult,
            "LineEstimation": LineEstimation,
            "LineMatch": LineMatch,
            "StopEstimationsResult": StopEstimationsResult,
            "StopMatch": StopMatch,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
