"""Project path utilities for the book-animations Blender project."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "project.json"


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def project_root() -> Path:
    return PROJECT_ROOT


def scenes_dir() -> Path:
    return PROJECT_ROOT / load_config()["paths"]["scenes"]


def characters_dir() -> Path:
    return PROJECT_ROOT / load_config()["paths"]["characters"]


def assets_dir() -> Path:
    return PROJECT_ROOT / load_config()["paths"]["assets"]


def renders_dir() -> Path:
    return PROJECT_ROOT / load_config()["paths"]["renders"]


def main_blend_path() -> Path:
    return PROJECT_ROOT / load_config()["paths"]["main_blend"]


def ensure_directories() -> None:
    for path in (scenes_dir(), characters_dir(), assets_dir(), renders_dir()):
        path.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_directories()
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Scenes:       {scenes_dir()}")
    print(f"Characters:   {characters_dir()}")
    print(f"Assets:       {assets_dir()}")
    print(f"Renders:      {renders_dir()}")
    print(f"Main blend:   {main_blend_path()}")