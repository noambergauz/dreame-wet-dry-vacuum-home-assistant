"""Import the component's modules without executing the package __init__.py.

custom_components/dreame_wet_dry_vacuum/__init__.py imports homeassistant,
which is neither needed by these unit tests nor installed in CI. Pre-register
stub package objects (with the right __path__) so that submodule imports like
`custom_components.dreame_wet_dry_vacuum.const` resolve directly to the module
files, skipping the package __init__.
"""
import sys
import types
from pathlib import Path

_COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "dreame_wet_dry_vacuum"

_cc = types.ModuleType("custom_components")
_cc.__path__ = [str(_COMPONENT_DIR.parent)]
_pkg = types.ModuleType("custom_components.dreame_wet_dry_vacuum")
_pkg.__path__ = [str(_COMPONENT_DIR)]

sys.modules.setdefault("custom_components", _cc)
sys.modules.setdefault("custom_components.dreame_wet_dry_vacuum", _pkg)
