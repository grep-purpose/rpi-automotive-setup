# Mira – Raspberry Pi im Audi A4 B7 / RNS-E 193

Ziel ist ein möglichst OEM-nahes Infotainment: HUDIY stellt die Android-Auto-Basis bereit, Kodi das Mediencenter. Globale Mira-Funktionen verbinden Bedienung, FIS und Medien mit dem Fahrzeug. Angeschlossen ist laut Projektbeschreibung derzeit der Infotainment-CAN.

Dieses Repository enthält Quellcode, Konfigurationen, Startdateien und gesicherte Varianten. **Es ist kein vollständig installierbares Abbild des laufenden Pi.** Eine vorhandene systemd-Datei beweist nicht, dass der Dienst installiert oder eingeschaltet ist.

## Hier anfangen

| Ich suche … | Einstieg |
|---|---|
| Überblick und Zusammenhänge | [Architektur](docs/ARCHITEKTUR.md) |
| Rückfahrkamera, Videoquellenumschaltung und OPS/PDC | [Das zusammenhängende Parking-System](docs/PARKING.md) |
| Welche Datei gehört wohin? | [Navigation und alte/neue Pfade](docs/PFADZUORDNUNG.md) |
| Welche Dienste starten was? | [Startwege und Abhängigkeiten](docs/STARTWEGE.md) |
| Was ist belegt, widersprüchlich oder fehlt? | [Prüfbefunde](docs/PRUEFBEFUNDE.md) |
| Sicherung und Wiederherstellung per Windows/SSH | [Recovery-Leitfaden](recovery/README.md) |

## Fachliche Bereiche

- **Kodi:** [Konfiguration, Add-ons und Oberfläche](apps/kodi), einschließlich Wetter, Radio und Medienanbindung.
- **HUDIY:** [Integrationsskripte und Menükonfiguration](apps/hudiy/integration); Bezugsquelle und Nutzungsrechte externer Bestandteile bleiben gesondert zu klären.
- **Mira Core:** globale Tastensteuerung, FIS und Medienkoordination; unter [mira-core/](mira-core) mit Querverbindung zur [Vehicle-Schicht](vehicle).
- **Vehicle:** CAN-Anbindung, Fahrzeugdaten, Zeit und Stromversorgung.
- **Parking:** Kamera, OPS/PDC und Videoquellenumschaltung bilden **ein System**, mit mehreren vorhandenen Softwarepfaden und noch ungeklärter externer Hardwareverknüpfung.
- **Boot/Launcher:** [Startauswahl](platform/launcher), [Animation und Übergänge](platform/boot), [Display-/EDID-Hardware](platform/display).
- **Recovery:** [gesicherte Konfigurationen und Wiederanlauf](recovery).

Die Dateien sind tatsächlich nach Funktionen eingeordnet. Bestehende Startpfade unter `launcher/` und `scripts/` bleiben als kleine Kompatibilitätseinstiege erhalten. `scripts/features.conf` bleibt die führende Laufzeitkonfiguration; der private Ordner `scripts/hudiy_api/` bleibt lokal. Diese Ausnahmen nicht löschen.

```text
apps/         Kodi und HUDIY-Integration
mira-core/    Eingabe, FIS, Medien, Steuerung und Integration
vehicle/      CAN, Stromversorgung und Plattformkonfiguration
parking/      Kamera, Videoquellenumschaltung und OPS/PDC gemeinsam
platform/     Boot, Launcher, Display und Sitzung
deployment/   systemd und gesicherte Unit-Varianten
recovery/     Sicherungen und Wiederherstellung
docs/         Architektur, Befunde und Pfadinventar
tools/        Diagnose und Strukturprüfung
```

[Umstellung, Kompatibilität und Rollback](docs/UMSTELLUNG.md). [Alle alten und neuen Dateipfade](docs/path-migration.json).

## Stand und Grenzen

Quellprüfung vom 15.10.2026, Basis main bei [9abba0b](https://github.com/grep-purpose/rpi-automotive-setup/tree/9abba0b2790ebfdeee3efe1a1fbe9b17ea250104). Code, systemd, Cron und Konfigurationen wurden statisch abgeglichen. Zusätzlich wurden vom Betreiber gelieferte systemd-, Cron-, labwc- und Pfadauflösungs-Ausgaben ausgewertet. Kein eigener Zugriff auf den Pi, kein Fahrzeug- oder Boot-Test. Besonders CAN-Signale, externe Parking-Hardware und aktive Startwege benötigen Bestätigung am Fahrzeug.

Es werden keine zusätzlichen HUDIY-Binärdateien, SDK-Dateien oder Zugangsdaten für diese Dokumentation übernommen. [Herkunft und offene Rechtefragen](recovery/HUDIY_SOURCE.md).

## Bekannter Bedienungsprüfpunkt

Die bisherige README nennt ein Problem mit Previous-Track als Backspace/Delete in Kodis WLAN-Tastatur. Dieser Lauf hat es nicht am Gerät reproduziert; es bleibt ein offener Bedienungsprüfpunkt.
