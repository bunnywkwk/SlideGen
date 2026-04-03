from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType

from .constants import LEGACY_LYRICS_DIR, LEGACY_VERSES_DIR


def _load_module(module_name: str, module_path: Path) -> ModuleType:
    spec = spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")

    module = module_from_spec(spec)
    # Register the module before execution so decorators and introspection behave normally.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def load_lyrics_core() -> ModuleType:
    return _load_module("legacy_lyrics_core", LEGACY_LYRICS_DIR / "generate_lyrics_ppt.py")


@lru_cache(maxsize=1)
def load_verses_core() -> ModuleType:
    return _load_module("legacy_verses_core", LEGACY_VERSES_DIR / "generate_verses_ppt.py")
