# Android-Auto-DPI in MIRA

Setup → Anzeige → Android Auto öffnet ein eigenes MIRA-Pop-up.
Gestaltungsvorlage ist das vorhandene USB-Auswurf-Pop-up aus
`apps/kodi/skin.estuary.custom/xml/custom_MiraUSBEjectConfirm.xml`:
abgedunkelter Hintergrund, zwei abgerundete Panel-Ebenen, dieselben
Transport-Texturen und große Skin-Schriften. Das globale Kodi-Auswahlfenster
wird nicht verändert.
Die Zeile zeigt den aus HUDIYs Konfiguration gelesenen DPI-Wert rechts an.
Auswahl: 140, 150, 160, 170, 180, 190 und 200 DPI. Der aktuelle Wert ist
vorausgewählt, sofern er in dieser Liste liegt. Abbrechen ändert nichts.
Bei einem gespeicherten Wert außerhalb der Liste startet der Fokus auf 140;
der tatsächliche aktuelle Wert bleibt im Kopf sichtbar. Drücken einer Zeile
übernimmt sie, Return/Zurück schließt ohne Speichern. Der Hinweis zur
Übernahme beim nächsten Android-Auto-Start bleibt im Pop-up sichtbar.

Das verfeinerte Layout rückt die Fläche weiter vom MIRA-Footer ab,
vergrößert die DPI-Schrift auf font60 mit Fettschrift. Der Übernahmehinweis
steht einzeilig unter einer dezenten Trennlinie. Die zusätzliche Bedienhilfe
wurde entfernt. Der gespeicherte Wert wird nur in der Liste als „Aktuell“
markiert; die Unterüberschrift lautet schlicht „Darstellungsgröße“.
Eine eigene rechteckige Auswahltextur mit kleinen Eckradien ersetzt die
bisherige pillenförmige Markierung. Die Maße sind Skin-Koordinaten;
die Darstellung auf dem RNS-E wird vom Betreiber geprüft.

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

Zusätzlich wird das Pop-up-Layout benötigt:

- `apps/kodi/userdata/scripts/resources/skins/default/1080i/MiraAndroidAutoDPI.xml`
- `apps/kodi/userdata/scripts/resources/media/mira_dpi_focus_rect.png`

Die Repository-Verzeichnisstruktur beibehalten und im Repository-Hauptverzeichnis
ausführen:

```bash
python3 tools/install_mira_android_auto_settings.py
```

Der Installer prüft den aktiven Skin, den bestehenden Platzhalter bzw. die
bereits installierte Zeile, Python-Syntax und XML. Er ändert die lokale
`custom_Display.xml` gezielt und installiert das Kodi-Skript samt eigenem
XML-Dialog unter den Skript-Ressourcen. Der Installer
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

Das stellt Menüdatei, Skript und Pop-up-XML auf den Stand vor dieser
Installation zurück bzw. entfernt neu angelegte Dateien. Beim Upgrade vom
ersten DPI-Menü wird dadurch die vorherige Kodi-Auswahl wiederhergestellt.
Ein bereits gewählter DPI-Wert bleibt dabei erhalten.
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

Die Dateisperre wird ausschließlich während des kurzen Speichervorgangs
gehalten und im finally-Block explizit freigegeben. Während des modalen
Pop-ups bleibt sie frei. Eine belegte Schreibsperre erzeugt eine sichtbare
Fehlermeldung statt eines stillen Abbruchs.

In einer Betreiberdiagnose vom 30.10.2026 hielt der Kodi-Prozess die alte,
über die gesamte Pop-up-Laufzeit gehaltene Sperre. Zum Freigeben dieses
bereits bestehenden Zustands muss der haltende Kodi-Prozess beendet werden;
ein einmaliger Pi-Neustart gibt sie ebenfalls frei. Die Sperrdatei muss
nicht gelöscht werden. Welcher konkrete GUI-Ablauf die alte Instanz
zurückließ, ist nicht abschließend nachgewiesen.

## Prüfung

```bash
python3 -m unittest discover -s tests -p 'test_android_auto_settings.py' -v
```

Fünfzehn lokale Tests mit nachgebildeter Kodi-API prüfen unter anderem
Abbrechen/Vorauswahl, Wertebereich, unveränderte Fremdeinstellungen,
Backups, laufendes bzw. startendes HUDIY, Pop-up-Vorauswahl und
Return/Zeilenbestätigung sowie Installation, Upgrade und Rollback.
Zusätzliche Regressionstests prüfen Öffnen/Abbrechen bei alter belegter
Sperre, sichtbaren Schreibfehler und Freigabe nach Speicherfehler.
Python und XML sind statisch geprüft. GUI-Darstellung, RNS-E-Drehradbedienung
und tatsächliche Übernahme beim nächsten HUDIY-Start müssen auf dem Pi
geprüft werden.
