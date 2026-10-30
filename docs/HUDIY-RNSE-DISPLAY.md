# HUDIY-Anzeigekalibrierung am RNS-E 193

Stand: 30.10.2026. Werte aus der vom Betreiber über SSH ausgelesenen Konfiguration.
Der Betreiber hat die Randanpassung als passend bestätigt; anschließend wurden 150 DPI eingestellt und ausgelesen. Eine gesonderte visuelle Bestätigung für 150 DPI liegt in diesem Protokoll nicht vor.

## Gesicherter Umfang

Die [Teilkonfiguration](../apps/hudiy/integration/config/rns-e-display.partial.json) enthält alle heute geänderten Anzeigeparameter sowie die ausgelesenen zugehörigen Fenster-, Leisten- und Streamparameter. Sie ist **kein vollständiger Ersatz** für `main_configuration.json`.

- Pi-Ausgabe: 800 × 480, Skalierung 1, HDMI-A-1, laut gelieferter Diagnose.
- Native HUDIY-Fläche und Android Auto: 784 × 468, X = 10, Y = 0.
- Android Auto: 480p, 150 DPI, 30 FPS, widthMargin = 16, heightMargin = 12.
- Rechnerischer Rest zur 800 × 480-Ausgabe: links 10, rechts 6, unten 12 Pixel.
- Fenstergröße bleibt automatisch; framelessWindow = true und splitWithProjections = false.
- bottomBarHeight = 100 wurde ausgelesen und unverändert übernommen; seine Bedeutung wurde hier nicht experimentell geprüft.

Die digitale Vollbildaufnahme zeigte den App-Menükreis vollständig, das Foto des RNS-E einen unteren Beschnitt. Beim Verkleinern allein der Projektionsfläche wurde native HUDIY-Bedienung sichtbar. Nach Anpassung von Stream-Rändern, Projektion und nativer HUDIY-Fläche bestätigte der Betreiber eine passende Darstellung. Rechts wurde anschließend um 4 Pixel erweitert.

Die Ursache des Beschnitts im nachfolgenden Ausgabeweg wurde nicht separat vermessen. Die Einstellungen gelten für diesen Aufbau. Kodi, MIRA-Skin und globale Displaykonfiguration wurden in dieser Sitzung nicht geändert.

## Wiederherstellen über SSH

Android Auto trennen und HUDIY vollständig beenden. Diesen Block auf dem Pi ausführen. Er lädt ausschließlich die Anzeige-Teilkonfiguration, sichert die vorhandene vollständige Konfiguration lokal und übernimmt nur die aufgeführten Schlüssel. Zugangsdaten und andere Einstellungen bleiben erhalten.

```bash
python3 - <<'PY'
import json
import shutil
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

url = "https://raw.githubusercontent.com/grep-purpose/rpi-automotive-setup/main/apps/hudiy/integration/config/rns-e-display.partial.json"
with urlopen(url, timeout=30) as response:
    patch = json.load(response)

allowed = {
    "application": {"windowWidth", "windowHeight", "width", "height",
                    "x", "y", "framelessWindow", "splitWithProjections"},
    "appearance": {"bottomBarHeight"},
    "androidAuto": {"resolution", "dpi", "width", "height", "x", "y",
                    "widthMargin", "heightMargin", "fps"}
}
if set(patch) != set(allowed):
    raise SystemExit("Abbruch: Unerwartete Abschnitte.")
for section, keys in allowed.items():
    if not isinstance(patch[section], dict) or set(patch[section]) != keys:
        raise SystemExit("Abbruch: Unerwartete Schlüssel unter " + section)

p = Path.home() / ".hudiy/share/config/main_configuration.json"
data = json.loads(p.read_text())
for section in patch:
    if not isinstance(data.get(section), dict):
        raise SystemExit("Abbruch: Fehlender Konfigurationsabschnitt " + section)

backup = p.with_name(
    p.name + ".before-display-restore-" +
    datetime.now().strftime("%Y%m%d-%H%M%S-%f")
)
shutil.copy2(p, backup)
for section, values in patch.items():
    data[section].update(values)
try:
    p.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n")
    assert json.loads(p.read_text()) == data
except Exception:
    shutil.copy2(backup, p)
    raise
print("Anzeigeeinstellungen übernommen und geprüft.")
print("Lokales Backup:", backup)
print("HUDIY starten und Android Auto neu verbinden.")
PY
```

Kein Pi-Neustart und kein Kodi-Reload erforderlich für diesen Ablauf.

## Letzte Wiederherstellung rückgängig machen

HUDIY vollständig beenden. Der folgende Block stellt die vollständige Konfiguration aus dem letzten Backup dieses Wiederherstellungsbefehls wieder her. Spätere Änderungen an dieser Konfiguration würden dabei ebenfalls zurückgenommen.

```bash
python3 - <<'PY'
import json
import shutil
from pathlib import Path

p = Path.home() / ".hudiy/share/config/main_configuration.json"
backups = sorted(p.parent.glob(p.name + ".before-display-restore-*"))
if not backups:
    raise SystemExit("Kein passendes Wiederherstellungsbackup gefunden.")
backup = backups[-1]
expected = json.loads(backup.read_text())
shutil.copy2(backup, p)
assert json.loads(p.read_text()) == expected
print("Wiederhergestellt aus:", backup)
print("HUDIY wieder starten.")
PY
```
