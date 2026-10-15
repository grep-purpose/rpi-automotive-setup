#!/usr/bin/env python3
"""Compatibility entry point; implementation: mira-core/integration/read_from_canbus.py."""
from pathlib import Path as _MiraPath
import sys as _mira_sys
_mira_source = (_MiraPath(__file__).resolve().parent / '../mira-core/integration/read_from_canbus.py').resolve()
_mira_sys.path.insert(0, str(_mira_source.parent))
exec(compile(_mira_source.read_bytes(), __file__, "exec"), globals(), globals())
