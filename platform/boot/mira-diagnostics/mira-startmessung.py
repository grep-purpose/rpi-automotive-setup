#!/usr/bin/env python3
"""Add removable startup timing only; does not change service ordering."""
import ast
from datetime import datetime
from pathlib import Path
import os
import shutil
import sys


def launcher_trace(text):
    if 'MIRA_TRACE' in text:
        raise RuntimeError('Launcher enthält bereits die Messung.')
    ast.parse(text)
    prefix = '''# MIRA_TRACE: monotonic seconds since boot
import time as _mira_trace_time
def _mira_trace(label):
    print("MIRA_TRACE %.3f %s" % (_mira_trace_time.monotonic(), label), flush=True)
_mira_trace("PYTHON_ENTRY")
'''
    if text.startswith('#!'):
        first, text = text.split('\n', 1)
        text = first + '\n' + prefix + text
    else:
        text = prefix + text
    needle = 'BASE_DIR = os.path.dirname('
    if text.count(needle) != 1:
        raise RuntimeError('BASE_DIR nicht eindeutig gefunden.')
    text = text.replace(needle, '_mira_trace("IMPORTS_DONE")\n\n' + needle, 1)
    tree = ast.parse(text)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    lines = text.splitlines(keepends=True)
    inserts = []
    app_node = next(n for n in main.body if isinstance(n, ast.Assign)
                    and isinstance(n.value, ast.Call)
                    and isinstance(n.value.func, ast.Name) and n.value.func.id == 'QApplication')
    launcher_node = next(n for n in main.body if isinstance(n, ast.Assign)
                         and isinstance(n.value, ast.Call)
                         and isinstance(n.value.func, ast.Name) and n.value.func.id == 'AudiLauncher')
    inserts.append((app_node.lineno - 1, '    _mira_trace("QAPPLICATION_BEGIN")\n'))
    inserts.append((app_node.end_lineno, '    _mira_trace("QAPPLICATION_DONE")\n'))
    inserts.append((launcher_node.lineno - 1, '    _mira_trace("LAUNCHER_BEGIN")\n'))
    inserts.append((launcher_node.end_lineno, '''    _mira_trace("LAUNCHER_CREATED")
    def _mira_first_swap():
        _mira_trace("FIRST_FRAME_SWAPPED")
        launcher.frameSwapped.disconnect(_mira_first_swap)
    launcher.frameSwapped.connect(_mira_first_swap)
'''))
    for index, insertion in sorted(inserts, reverse=True):
        lines.insert(index, insertion)
    result = ''.join(lines)
    ast.parse(result)
    return result


def autostart_trace(text):
    if 'MIRA_TRACE' in text:
        raise RuntimeError('Autostart enthält bereits die Messung.')
    if not text.startswith('#!/bin/sh\n'):
        raise RuntimeError('Unerwarteter Autostart-Kopf.')
    marker = '''# MIRA_TRACE: timestamp before starting any applications
read mira_uptime mira_idle < /proc/uptime
/usr/bin/logger -t mira-start "MIRA_TRACE $mira_uptime AUTOSTART_ENTRY"
'''
    return text.replace('#!/bin/sh\n', '#!/bin/sh\n' + marker, 1)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--check':
        result = launcher_trace(Path(sys.argv[2]).read_text())
        assert result.count('launcher.frameSwapped.connect(_mira_first_swap)') == 1
        print('Launcher-Patch und Python-Syntax geprüft.')
        sys.exit(0)
    if os.geteuid() != 0:
        raise SystemExit('Bitte mit sudo python3 ausführen.')
    try:
        launcher = Path('/home/pi/rpi-automotive-setup/launcher/boot_launcher.py')
        autostart = Path('/etc/xdg/labwc/autostart')
        for p in (launcher, autostart):
            if p.is_symlink() or not p.is_file():
                raise RuntimeError('Reguläre Datei erwartet: ' + str(p))
        changes = [(launcher, launcher_trace(launcher.read_text())),
                   (autostart, autostart_trace(autostart.read_text()))]
        backup = Path('/var/backups') / ('mira-startmessung-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        backup.mkdir(mode=0o700)
        for p, _ in changes:
            shutil.copy2(p, backup / p.name)
        try:
            for p, text in changes:
                # In-place write retains original owner and permissions.
                p.write_text(text)
        except Exception:
            for p, _ in changes:
                shutil.copyfile(backup / p.name, p)
            raise
        print('OK: Messung eingebaut. Kein Dienst wurde neu gestartet.')
        print('Sicherung: ' + str(backup))
    except Exception as exc:
        raise SystemExit('ABBRUCH: ' + str(exc))
