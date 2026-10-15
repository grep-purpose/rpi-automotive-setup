# Mira – Raspberry Pi im Audi A4 B7 / RNS-E 193

Ziel ist ein möglichst OEM-nahes Infotainment: HUDIY stellt die Android-Auto-Basis bereit, Kodi das Mediencenter. Globale Mira-Funktionen verbinden Bedienung, FIS und Medien mit dem Fahrzeug. Angeschlossen ist laut Projektbeschreibung derzeit der Infotainment-CAN.

Dieses Repository enthält Quellcode, Konfigurationen, Startdateien und gesicherte Varianten. **Es ist kein vollständig installierbares Abbild des laufenden Pi.** Eine vorhandene systemd-Datei beweist nicht, dass der Dienst installiert oder eingeschaltet ist.

## Hier anfangen

| Ich suche … | Einstieg |
|---|---|
| Überblick und Zusammenhänge | [Architektur](docs/ARCHITEKTUR.md) |
| Rückfahrkamera, Videoquellenumschaltung und OPS/PDC | [Das zusammenhängende Parking-System](docs/PARKING.md) |
| Welche Datei gehört wohin? | [Navigation und vorgeschlagene Pfade](docs/PFADZUORDNUNG.md) |
| Welche Dienste starten was? | [Startwege und Abhängigkeiten](docs/STARTWEGE.md) |
| Was ist belegt, widersprüchlich oder fehlt? | [Prüfbefunde](docs/PRUEFBEFUNDE.md) |
| Sicherung und Wiederherstellung per Windows/SSH | [Recovery-Leitfaden](recovery/README.md) |

## Fachliche Bereiche

- **Kodi:** [Konfiguration, Add-ons und Oberfläche](kodi/), einschließlich Wetter, Radio und Medienanbindung.
- **HUDIY:** [Integrationsskripte und Menükonfiguration](hudiy/); Bezugsquelle und Nutzungsrechte externer Bestandteile bleiben gesondert zu klären.
- **Mira Core:** globale Tastensteuerung, FIS und Medienkoordination; heute über [CAN-Code](can/rns-e_can/), [FIS-Code](dis_client/) und [Skripte](scripts/) verteilt.
- **Vehicle:** CAN-Anbindung, Fahrzeugdaten, Zeit und Stromversorgung.
- **Parking:** Kamera, OPS/PDC und Videoquellenumschaltung bilden **ein System**, mit mehreren vorhandenen Softwarepfaden und noch ungeklärter externer Hardwareverknüpfung.
- **Boot/Launcher:** [Startauswahl](launcher/), [Animation und Übergänge](boot/), [Display-/EDID-Hardware](vga-edid/).
- **Recovery:** [gesicherte Konfigurationen und Wiederanlauf](recovery/).

Diese Gliederung beschreibt Zuständigkeiten. Sie verschiebt keine Dateien und ändert keine produktiven Pfade.

## Stand und Grenzen

Quellprüfung vom 15.10.2026, Basis main bei [9abba0b](https://github.com/grep-purpose/rpi-automotive-setup/tree/9abba0b2790ebfdeee3efe1a1fbe9b17ea250104). Code, systemd, Cron und Konfigurationen wurden statisch abgeglichen. Kein Zugriff auf den laufenden Pi, kein Fahrzeug- oder Boot-Test. Besonders CAN-Signale, externe Parking-Hardware und aktive Startwege benötigen Bestätigung am Fahrzeug.

Es werden keine zusätzlichen HUDIY-Binärdateien, SDK-Dateien oder Zugangsdaten für diese Dokumentation übernommen. [Herkunft und offene Rechtefragen](recovery/HUDIY_SOURCE.md).

## Bekannter Bedienungsprüfpunkt

Die bisherige README nennt ein Problem mit Previous-Track als Backspace/Delete in Kodis WLAN-Tastatur. Dieser Lauf hat es nicht am Gerät reproduziert; es bleibt ein offener Bedienungsprüfpunkt.
