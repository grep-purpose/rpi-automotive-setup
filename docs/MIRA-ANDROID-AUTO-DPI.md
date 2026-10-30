# Android-Auto-DPI in MIRA

Setup → Anzeige → Android Auto öffnet das vorhandene Kodi-Auswahlfenster.
Die Zeile zeigt den aus HUDIYs Konfiguration gelesenen DPI-Wert rechts an.
Auswahl: 140, 150, 160, 170, 180, 190 und 200 DPI. Der aktuelle Wert ist
vorausgewählt, sofern er in dieser Liste liegt. Abbrechen ändert nichts.

Eine bestätigte Auswahl wird für den nächsten Start von HUDIY/Android Auto
gespeichert. Die Funktion startet keine Anwendung neu. Sie ändert ausschließlich
`androidAuto.dpi` in `~/.hudiy/share/config/main_configuration.json`.
Bildränder, Projektionsfläche, native HUDIY-Fläche und andere Einstellungen
bleiben erhalten. Die Auswahlgrenzen sind MIRA-Testwerte; nicht jeder Wert
wurde am RNS-E visuell geprüft.

## Installation auf dem Pi

MIRA/Kodi geöffnet lassen; als Benutzer `pi` ohne sudo ausführen.
Der Installer benötigt die beiden Dateien aus diesem Repository:

- `tools/install_mira_android_auto_settings.py`
- `apps/kodi/userdata/scripts/mira_android_auto_settings.py`

Die Repository-Verzeichnisstruktur beibehalten und im Repository-Hauptverzeichnis
ausführen:

```bash
python3 tools/install_mira_android_auto_settings.py
```

Der Installer prüft den aktiven Skin, den bestehenden Platzhalter bzw. die
bereits installierte Zeile, Python-Syntax und XML. Er ändert die lokale
`custom_Display.xml` gezielt und installiert das Kodi-Skript. Der Installer
übernimmt keine vollständige Skin-Datei vom Server über die lokale Fassung.
Nach erfolgreicher Installation wird `kodi-send --action="ReloadSkin()"`
ausgeführt. Ein Pi-Neustart ist nicht erforderlich.

## Backups und Rückweg

Vor der Installation werden die betroffenen Dateien sowie die aktuelle
HUDIY-Konfiguration lokal gesichert unter:

`~/.local/state/mira/android-auto-settings-backups/<Zeitstempel>/`

Diese privaten Konfigurationsbackups werden nicht auf GitHub hochgeladen.

Die letzte Installation zurücknehmen:

```bash
python3 tools/install_mira_android_auto_settings.py --rollback
```

Das stellt Menüdatei und vorheriges Skript wieder her bzw. entfernt das neu
installierte Skript. Ein bereits gewählter DPI-Wert bleibt dabei erhalten.
Kodi wird anschließend erneut geladen.

Vor jeder tatsächlichen DPI-Änderung sichert das Kodi-Skript die ursprüngliche
Konfiguration zusätzlich unter:

`~/.hudiy/share/config/mira-dpi-backups/`

Die Dateien haben Zugriffsmodus 0600. Schreiben erfolgt über eine temporäre
Datei im selben Verzeichnis mit atomarem Ersetzen. Vor der Auswahl und vor
dem Speichern wird auf einen Prozess namens `hudiy` geprüft. Eine während
der Auswahl geänderte DPI oder vor dem Ersetzen geänderte Konfiguration
führt zum Abbruch statt zum Überschreiben. Diese Prüfungen ersetzen keine
gemeinsame Sperre mit einem externen HUDIY-Starter.

## Prüfung

```bash
python3 -m unittest discover -s tests -p 'test_android_auto_settings.py' -v
```

Neun lokale Tests mit nachgebildeter Kodi-API prüfen unter anderem
Abbrechen/Vorauswahl, Wertebereich, unveränderte Fremdeinstellungen,
Backups, laufendes bzw. startendes HUDIY sowie Installation und Rollback.
Python und XML sind statisch geprüft. GUI-Darstellung, RNS-E-Drehradbedienung
und tatsächliche Übernahme beim nächsten HUDIY-Start müssen auf dem Pi
geprüft werden.
