from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path


PACKAGE_NAME = "aucorsa-api"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "aucorsa" / "manifest.json"


def get_version() -> str:
    """Return the integration version using manifest.json as the source of truth."""
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        version = str(manifest["version"]).strip()
        if version:
            return version
    except (OSError, ValueError, KeyError, TypeError):
        pass

    try:
        return package_version(PACKAGE_NAME)
    except PackageNotFoundError as exc:
        raise RuntimeError("Unable to resolve the Aucorsa version") from exc
