#!/usr/bin/env python3
"""Install the MIRA DPI selector, or restore its last installation backup."""

import ast
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

SCRIPT = "mira_android_auto_settings.py"
RESOURCE = Path("resources/skins/default/1080i/MiraAndroidAutoDPI.xml")
ACTION = "RunScript(/home/pi/.kodi/userdata/scripts/" + SCRIPT + ",select)"
SYNC = "RunScript(/home/pi/.kodi/userdata/scripts/" + SCRIPT + ",sync)"


def patched_xml(text):
    root = ET.fromstring(text)
    if root.get("id") != "1157":
        raise ValueError("Unerwartete Fenster-ID; keine Änderung")
    old = re.compile(
        r'<item>\s*<label>Anzeigeeinstellungen</label>\s*'
        r'<property name="RowType">action</property>\s*'
        r'<onclick>Notification\(Anzeige,Anzeigeeinstellungen folgen,2000\)</onclick>\s*</item>'
    )
    replacement = '''<item>
                    <label>Android Auto</label>
                    <label2>$INFO[Window(Home).Property(RNSE.AndroidAuto.DPI),, DPI]</label2>
                    <property name="RowType">submenu</property>
                    <onclick>''' + ACTION + '''</onclick>
                </item>'''
    count = len(old.findall(text))
    if count == 1:
        text = old.sub(lambda _: replacement, text, count=1)
    elif count == 0 and any(
        item.findtext("label") == "Android Auto" and
        item.findtext("onclick") == ACTION
        for item in root.findall(".//content/item")
    ):
        pass
    else:
        raise ValueError("Platzhalter fehlt oder ist nicht eindeutig; keine Änderung")
    # Match the common settings row kit: leave space for the submenu chevron.
    text = text.replace("<width>920</width>", "<width>820</width>")
    if SYNC not in text:
        text, count = re.subn(
            r'(<defaultcontrol\b)', '<onload>' + SYNC + '</onload>\n    \\1',
            text, count=1
        )
        if count != 1:
            raise ValueError("Kein passender onload-Einstieg")
    checked = ET.fromstring(text)
    if not any(node.text == SYNC for node in checked.findall("onload")):
        raise ValueError("XML-Prüfung: onload fehlt")
    return text


def write_atomic(path, payload, mode):
    fd, name = tempfile.mkstemp(prefix=".mira-aa-install-", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def restore(backup, home):
    manifest = json.loads((backup / "manifest.json").read_text())
    for entry in manifest:
        target = home / entry["target"]
        if entry["existed"]:
            saved = backup / entry["saved"]
            write_atomic(target, saved.read_bytes(), saved.stat().st_mode & 0o777)
        else:
            target.unlink(missing_ok=True)


def install(home, source):
    settings = ET.parse(home / ".kodi/userdata/guisettings.xml").getroot()
    skin = next((node.text for node in settings.iter("setting")
                 if node.get("id") == "lookandfeel.skin"), None)
    if skin != "skin.estuary.custom":
        raise ValueError("Aktiver Skin ist nicht skin.estuary.custom; keine Änderung")
    xml = home / ".kodi/addons/skin.estuary.custom/xml/custom_Display.xml"
    target = home / ".kodi/userdata/scripts" / SCRIPT
    helper = source / "apps/kodi/userdata/scripts" / SCRIPT
    resource = target.parent / RESOURCE
    resource_source = source / "apps/kodi/userdata/scripts" / RESOURCE
    resource_code = resource_source.read_bytes()
    ET.fromstring(resource_code)
    original = xml.read_bytes()
    updated = patched_xml(original.decode("utf-8")).encode("utf-8")
    code = helper.read_bytes()
    ast.parse(code.decode("utf-8"))
    config = home / ".hudiy/share/config/main_configuration.json"
    dpi = json.loads(config.read_text())["androidAuto"]["dpi"]
    if type(dpi) is not int:
        raise ValueError("Gespeicherte DPI ungültig; keine Änderung")
    for path in (xml, target, resource):
        if path.is_symlink():
            raise ValueError("Verknüpfte Zieldatei: " + str(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    resource.parent.mkdir(parents=True, exist_ok=True)
    backup_root = home / ".local/state/mira/android-auto-settings-backups"
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = backup_root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(mode=0o700)
    manifest = []
    for index, path in enumerate((xml, target, resource)):
        entry = {"target": str(path.relative_to(home)),
                 "existed": path.exists(), "saved": str(index)}
        if path.exists():
            shutil.copy2(path, backup / str(index))
        manifest.append(entry)
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
    shutil.copy2(config, backup / "main_configuration.local-backup.json")
    (backup / "main_configuration.local-backup.json").chmod(0o600)
    try:
        write_atomic(resource, resource_code, 0o644)
        write_atomic(target, code, 0o644)
        write_atomic(xml, updated, xml.stat().st_mode & 0o777)
        assert target.read_bytes() == code
        assert xml.read_bytes() == updated
        assert resource.read_bytes() == resource_code
        ET.parse(xml)
        ET.parse(resource)
        ast.parse(target.read_text())
    except Exception:
        restore(backup, home)
        raise
    print("Installiert und geprüft: Eigenes MIRA-Pop-up für 140–200 DPI")
    print("HUDIY-Konfiguration unverändert; aktueller Wert:", dpi)
    print("Installationsbackup:", backup)
    return backup


def reload_skin():
    try:
        subprocess.run(["kodi-send", "--action=ReloadSkin()"],
                       check=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        print("Dateien bereit, Kodi-Reload fehlgeschlagen:", exc)
        print('Bitte manuell: kodi-send --action="ReloadSkin()"')


def main():
    home = Path.home()
    if str(home) != "/home/pi":
        raise ValueError("Bitte als Benutzer pi ohne sudo ausführen")
    if sys.argv[1:] == ["--rollback"]:
        root = home / ".local/state/mira/android-auto-settings-backups"
        backups = sorted(p for p in root.glob("*") if (p / "manifest.json").is_file())
        if not backups:
            raise ValueError("Kein Installationsbackup gefunden")
        restore(backups[-1], home)
        print("Letzte Installation zurückgenommen. Gewählter DPI-Wert bleibt erhalten.")
    elif not sys.argv[1:]:
        install(home, Path(__file__).resolve().parents[1])
    else:
        raise ValueError("Unbekanntes Argument")
    reload_skin()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit("Abbruch: " + str(exc))
