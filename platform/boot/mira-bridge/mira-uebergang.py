#!/usr/bin/env python3
"""Reversible Plymouth/Wayland still-image bridge for the inspected Pi."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

AUTOSTART = Path('/etc/xdg/labwc/autostart')
LIGHTDM = Path('/etc/lightdm/lightdm.conf.d/90-mira-vt.conf')
GETTY = Path('/etc/systemd/system/getty@tty1.service')
IMAGE = Path('/usr/share/plymouth/themes/mira/frame-0.png')
BACKUP = Path('/var/backups/mira-uebergang')
BLOCK = '''# BEGIN MIRA_BACKGROUND_BRIDGE
# Start behind applications; no browser or input capture.
if [ -x /usr/bin/swaybg ] && [ -r /usr/share/plymouth/themes/mira/frame-0.png ]; then
    /usr/bin/swaybg -i /usr/share/plymouth/themes/mira/frame-0.png -m fit -c '#101419' &
fi
# END MIRA_BACKGROUND_BRIDGE
'''


def patch_autostart(text):
    if not text.startswith('#!/bin/sh\n') or 'BEGIN MIRA_BACKGROUND_BRIDGE' in text:
        raise RuntimeError('Autostart-Kopf ist unerwartet oder bereits angepasst.')
    if 'python3 /home/pi/rpi-automotive-setup/launcher/boot_launcher.py' not in text:
        raise RuntimeError('Erwarteter Launcher-Aufruf fehlt.')
    return text.replace('#!/bin/sh\n', '#!/bin/sh\n' + BLOCK, 1)


def run(args):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=30).stdout


def restore():
    if not (BACKUP / 'ready').exists():
        raise RuntimeError('Keine vollständige Sicherung vorhanden.')
    original = BACKUP / 'autostart'
    expected = (BACKUP / 'autostart.sha256').read_text().strip()
    if hashlib.sha256(original.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Sicherung beschädigt; nichts wiederhergestellt.')
    if AUTOSTART.is_symlink():
        raise RuntimeError('Autostart ist inzwischen ein Symlink; Abbruch.')
    if LIGHTDM.exists() and LIGHTDM.read_text() != '[LightDM]\nminimum-vt=1\n':
        raise RuntimeError('LightDM-Datei wurde nachträglich geändert; Abbruch.')
    if GETTY.is_symlink() and os.readlink(GETTY) != '/dev/null':
        raise RuntimeError('Andere getty-Verknüpfung gefunden; Abbruch.')
    if GETTY.exists() and not GETTY.is_symlink():
        raise RuntimeError('Andere getty-Datei gefunden; Abbruch.')
    shutil.copyfile(original, AUTOSTART)
    if LIGHTDM.exists():
        LIGHTDM.unlink()
    if GETTY.is_symlink():
        GETTY.unlink()
    run(['systemctl', 'daemon-reload'])
    print('OK: Vorheriger Autostart, VT-Auswahl und tty1-Anmeldung wiederhergestellt.')
    print('Die Wiederherstellung wird beim nächsten Neustart vollständig wirksam.')


def install():
    for path in (LIGHTDM, GETTY, BACKUP):
        if path.exists() or path.is_symlink():
            raise RuntimeError('Ziel existiert bereits: ' + str(path))
    if not Path('/usr/bin/swaybg').is_file():
        raise RuntimeError('swaybg fehlt. Zuerst sudo apt install swaybg ausführen.')
    if not IMAGE.is_file() or IMAGE.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
        raise RuntimeError('Das vorhandene MIRA-Bild fehlt oder ist ungültig.')
    if not AUTOSTART.is_file() or AUTOSTART.is_symlink():
        raise RuntimeError('Reguläre Autostart-Datei erwartet.')
    changed = patch_autostart(AUTOSTART.read_text())
    syntax = subprocess.run(['/bin/sh', '-n'], input=changed, text=True,
                            capture_output=True, timeout=10)
    if syntax.returncode:
        raise RuntimeError('Shell-Syntaxprüfung fehlgeschlagen: ' + syntax.stderr)
    BACKUP.mkdir(mode=0o700)
    shutil.copy2(AUTOSTART, BACKUP / 'autostart')
    (BACKUP / 'autostart.sha256').write_text(hashlib.sha256(AUTOSTART.read_bytes()).hexdigest())
    (BACKUP / 'ready').write_text(datetime.now().isoformat())
    try:
        LIGHTDM.parent.mkdir(parents=True, exist_ok=True)
        LIGHTDM.write_text('[LightDM]\nminimum-vt=1\n')
        LIGHTDM.chmod(0o644)
        shown = run(['lightdm', '--show-config'])
        if not re.search(r'^\s*(?:[A-Z]+\s+)?minimum-vt\s*=\s*1\s*$', shown, re.M):
            raise RuntimeError('LightDM übernimmt minimum-vt=1 nicht.')
        # Do not stop any running service. Mask only the tty1 login on future boots.
        GETTY.symlink_to('/dev/null')
        run(['systemctl', 'daemon-reload'])
        status = subprocess.run(['systemctl', 'is-enabled', 'getty@tty1.service'],
                                text=True, capture_output=True, timeout=10)
        if status.stdout.strip() != 'masked':
            raise RuntimeError('tty1-Anmeldung wurde nicht wie erwartet maskiert.')
        AUTOSTART.write_text(changed)
    except Exception:
        restore()
        raise
    print('OK: MIRA-Überbrückung vorbereitet. Kein Dienst wurde gestoppt.')
    print('tty1-Textanmeldung ist ab dem nächsten Boot aus; SSH bleibt unverändert.')
    print('Sicherung: ' + str(BACKUP))


if __name__ == '__main__':
    if os.geteuid() != 0:
        raise SystemExit('Bitte mit sudo python3 ausführen.')
    try:
        if sys.argv[1:] == ['restore']:
            restore()
        elif not sys.argv[1:]:
            install()
        else:
            raise RuntimeError('Aufruf: mira-uebergang.py [restore]')
    except Exception as exc:
        print('ABBRUCH: ' + str(exc), file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stdout or '', file=sys.stderr)
        sys.exit(1)
