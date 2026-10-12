#!/usr/bin/env python3
"""Guarded installer for the inspected pi@192.168.0.59 setup. No reboot."""
import ast
import configparser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime

REPO = Path('/home/pi/rpi-automotive-setup')
LAUNCHER = REPO / 'launcher/boot_launcher.py'
MODULE = REPO / 'launcher/mira_splash.py'
REPO_ASSETS = REPO / 'boot/mira-animation'
THEME = Path('/usr/share/plymouth/themes/mira')
CONF = Path('/etc/plymouth/plymouthd.conf')
FIRMWARE = Path('/boot/firmware/initramfs8')
BACKUPS = Path('/var/backups/mira-boot')
RECOVERY = Path('/home/pi/mira-recovery')
SOURCE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=300).stdout


def replace_file(source, target, uid=None, gid=None, mode=None):
    tmp = target.with_name(target.name + '.mira-new')
    if tmp.exists() or tmp.is_symlink():
        raise RuntimeError('Temporäre Datei existiert bereits: ' + str(tmp))
    try:
        shutil.copy2(source, tmp)
        if uid is not None:
            os.chown(tmp, uid, gid)
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink()


def restore(folder):
    folder = folder.resolve()
    if folder.parent != BACKUPS.resolve():
        raise RuntimeError('Ungültiger Sicherungsordner.')
    entries = json.loads((folder / 'backup.json').read_text())
    allowed = {str(LAUNCHER), str(MODULE), str(CONF), str(FIRMWARE)}
    # Only kernel initrd backups created by this installer are accepted.
    for entry in entries:
        path = Path(entry['path'])
        if str(path) not in allowed and not (
            path.parent == Path('/boot') and path.name.startswith('initrd.img-')
        ):
            raise RuntimeError('Unerwartetes Wiederherstellungsziel.')
        if path.is_symlink():
            raise RuntimeError('Symlink als Wiederherstellungsziel: ' + str(path))
        if entry['exists'] and digest(folder / entry['file']) != entry['sha256']:
            raise RuntimeError('Sicherung beschädigt. Abbruch vor Wiederherstellung.')
    for entry in entries:
        path = Path(entry['path'])
        if entry['exists']:
            replace_file(folder / entry['file'], path,
                         entry['uid'], entry['gid'], entry['mode'])
        elif path.exists():
            path.unlink()
    print('Wiederhergestellt: Launcher, Plymouth-Konfiguration und Startdateien.')
    print('MIRA-Quelldateien im Repository bleiben für die Nachvollziehbarkeit erhalten.')


def install():
    manifest = json.loads((SOURCE / 'manifest.json').read_text())
    for relative, expected in manifest['files'].items():
        candidate = SOURCE / relative
        if candidate.is_symlink() or digest(candidate) != expected:
            raise RuntimeError('Paketprüfung fehlgeschlagen: ' + relative)
    kernel = os.uname().release
    if not kernel.endswith('rpi-v8'):
        raise RuntimeError('Dieses Paket ist für den geprüften rpi-v8-Kernel vorgesehen.')
    initrd = Path('/boot') / ('initrd.img-' + kernel)
    for path in (LAUNCHER, CONF, FIRMWARE, initrd):
        if not path.is_file() or path.is_symlink():
            raise RuntimeError('Reguläre Datei fehlt: ' + str(path))
    if digest(LAUNCHER) != manifest['original_launcher_sha256']:
        raise RuntimeError('Launcher hat sich seit dem Upload geändert. Keine Änderungen vorgenommen.')
    for path in (MODULE, REPO_ASSETS, THEME, RECOVERY):
        if path.exists() or path.is_symlink():
            raise RuntimeError('Ziel existiert bereits; keine Überschreibung: ' + str(path))
    if not (REPO / '.git').exists():
        raise RuntimeError('Git-Repository nicht gefunden.')
    if not list(Path('/usr/lib').glob('*/plymouth/script.so')):
        raise RuntimeError('Plymouth script.so fehlt. Ausgabe bitte weitergeben.')
    if digest(FIRMWARE) != digest(initrd):
        raise RuntimeError('initramfs8 und Kernel-initrd unterscheiden sich. Zuerst prüfen.')
    for command in ('update-initramfs', 'lsinitramfs'):
        if not shutil.which(command):
            raise RuntimeError(command + ' fehlt.')
    for mount in ('/boot/firmware', '/boot', '/home/pi'):
        if shutil.disk_usage(mount).free < 120 * 1024 * 1024:
            raise RuntimeError('Weniger als 120 MB frei: ' + mount)
    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    cfg.read(CONF)
    if cfg.get('Daemon', 'Theme', fallback='') != 'spinner':
        raise RuntimeError('Aktuelles Plymouth-Thema ist nicht mehr spinner. Zuerst prüfen.')
    for name in ('boot_launcher.py', 'mira_splash.py'):
        ast.parse((SOURCE / name).read_text())
    print(run(['/usr/bin/python3', '-c',
        'from PyQt5.QtWidgets import QApplication; from PyQt5.QtGui import QImage; '
        'import sys; im=QImage(sys.argv[1]); assert im.width()==800 and im.height()==480; '
        'print("PyQt5 und PNG-Unterstützung: OK")', str(SOURCE / 'theme/frame-0.png')]))
    BACKUPS.mkdir(parents=True, exist_ok=True)
    folder = BACKUPS / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(mode=0o700)
    entries = []
    for index, path in enumerate((LAUNCHER, MODULE, CONF, FIRMWARE, initrd)):
        entry = {'path': str(path), 'exists': path.exists()}
        if path.exists():
            stat = path.stat()
            name = str(index) + '.backup'
            shutil.copy2(path, folder / name)
            entry.update(file=name, sha256=digest(path), uid=stat.st_uid,
                         gid=stat.st_gid, mode=stat.st_mode & 0o7777)
        entries.append(entry)
    (folder / 'backup.json').write_text(json.dumps(entries, indent=2))
    shutil.copy2(SOURCE / 'install.py', folder / 'install.py')
    (BACKUPS / 'latest.txt').write_text(str(folder))
    print('Sicherung vollständig: ' + str(folder), flush=True)
    owner = LAUNCHER.stat()
    RECOVERY.mkdir(mode=0o755)
    shutil.copy2(FIRMWARE, RECOVERY / 'initramfs8')
    shutil.copy2('/boot/firmware/config.txt', RECOVERY / 'config.txt')
    for path in (RECOVERY, RECOVERY / 'initramfs8', RECOVERY / 'config.txt'):
        os.chown(path, owner.st_uid, owner.st_gid)
    print('Zusätzliche SD-Karten-Rettungskopie: ' + str(RECOVERY), flush=True)
    try:
        shutil.copytree(SOURCE, REPO_ASSETS)
        for path in [REPO_ASSETS] + list(REPO_ASSETS.rglob('*')):
            os.chown(path, owner.st_uid, owner.st_gid)
        shutil.copytree(SOURCE / 'theme', THEME)
        replace_file(SOURCE / 'mira_splash.py', MODULE, owner.st_uid, owner.st_gid, 0o644)
        replace_file(SOURCE / 'boot_launcher.py', LAUNCHER, owner.st_uid, owner.st_gid,
                     owner.st_mode & 0o7777)
        cfg.set('Daemon', 'Theme', 'mira')
        temp_conf = folder / 'new-plymouth.conf'
        with temp_conf.open('w') as stream:
            cfg.write(stream)
        replace_file(temp_conf, CONF, 0, 0, 0o644)
        print('Erzeuge Startdatei für ' + kernel + ' ...', flush=True)
        print(run(['update-initramfs', '-u', '-k', kernel]), flush=True)
        if digest(initrd) != digest(FIRMWARE):
            raise RuntimeError('Firmware-initramfs wurde nicht passend aktualisiert.')
        listing = run(['lsinitramfs', str(FIRMWARE)])
        for required in ('plymouth/themes/mira/mira.script',
                         'plymouth/themes/mira/frame-155.png',
                         'plymouth/script.so',
                         'pcbbc_Rpi_RNSE_800x480i_EDID.bin'):
            if required not in listing:
                raise RuntimeError('Fehlt in neuer Startdatei: ' + required)
        print('MIRA INSTALLIERT UND STARTDATEI GEPRÜFT. Noch kein Neustart erfolgt.')
    except Exception:
        print('Installation fehlgeschlagen. Stelle ursprüngliche Startdateien wieder her.', flush=True)
        restore(folder)
        raise


if __name__ == '__main__':
    if os.geteuid() != 0:
        raise SystemExit('Bitte mit sudo python3 ausführen.')
    try:
        if sys.argv[1:] == ['restore']:
            restore(Path((BACKUPS / 'latest.txt').read_text().strip()))
        elif not sys.argv[1:]:
            install()
        else:
            raise RuntimeError('Aufruf: install.py [restore]')
    except Exception as exc:
        print('ABBRUCH: ' + str(exc), file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stdout or '', file=sys.stderr)
        sys.exit(1)
