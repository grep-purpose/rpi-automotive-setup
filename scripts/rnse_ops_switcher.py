#!/usr/bin/env python3
"""Compatibility entry point; implementation: parking/video-switch/rnse_ops_switcher.py."""
from pathlib import Path as _MiraPath
import sys as _mira_sys
_mira_source = (_MiraPath(__file__).resolve().parent / '../parking/video-switch/rnse_ops_switcher.py').resolve()
_mira_sys.path.insert(0, str(_mira_source.parent))
exec(compile(_mira_source.read_bytes(), __file__, "exec"), globals(), globals())
