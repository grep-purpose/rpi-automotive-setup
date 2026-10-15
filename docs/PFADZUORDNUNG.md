# Navigation: vorhandene Dateien tatsächlich einsortiert

[Startseite](../README.md) · [Umstellung](UMSTELLUNG.md) · [Vollständiges Dateiinventar](path-migration.json)

Die folgende Gliederung ist umgesetzt. 1.422 bereits versionierte Dateien wurden verlagert. Das vollständige JSON-Inventar nennt für jede Datei der Dokumentationsbasis ihren alten und neuen Pfad. Doppelte Kodi-, Wetter- und Boot-Varianten bleiben getrennt; keine vermeintlichen Dubletten wurden gelöscht.

| Bisher | Jetzt | Zuständigkeit |
|---|---|---|
| kodi/ | [apps/kodi/](../apps/kodi/) | Kodi-Oberfläche, Add-ons, Konfiguration und Adapter |
| hudiy/ ohne api_files | [apps/hudiy/integration/](../apps/hudiy/integration/) | HUDIY-Adapter, Startskripte, Menüs |
| dis_client/ | [mira-core/fis/](../mira-core/fis/) | FIS-Seiten, Darstellung und DDP |
| can/rns-e_can/can_keyboard_control.py | [mira-core/input/](../mira-core/input/) | Globale Tastensteuerung |
| can/rns-e_can/can_handler.py | [vehicle/can/](../vehicle/can/) | CAN-Gateway und Parking-Sendesperre |
| can/rns-e_can/can_base_function.py | [vehicle/power-time/](../vehicle/power-time/) | TV-Präsenz, Uhr und Stromversorgung |
| can/audi-rns-overlay/ und scripts/rnse_ops_switcher.py | [parking/](../parking/) | Ein gemeinsames Parking-System |
| scripts/read_from_canbus.py und nav_icon_decoder.py | [mira-core/integration/](../mira-core/integration/) | Übergreifende Integration; Importpartner zusammengehalten |
| scripts/pi_control.py | [mira-core/control/](../mira-core/control/) | HTTP-Steuerung |
| USB-/Audio-Skripte und config/usb, config/audio | [mira-core/media/](../mira-core/media/) | Globale Medieninfrastruktur |
| Screenshot-Skripte und assets/ | [mira-core/diagnostics/screenshots/](../mira-core/diagnostics/screenshots/) | Aufnahme, Warteschlange und Ton |
| Wetter-Helfer an Wurzel und scripts/weather/ | [apps/kodi/weather-tools/](../apps/kodi/weather-tools/) | Wetter und GPS; Varianten getrennt |
| launcher/, boot/, vga-edid/, config/labwc/ | [platform/](../platform/) | Boot, Auswahl, Display, Sitzung |
| system/network/ | [vehicle/can/network/](../vehicle/can/network/) | CAN-Netzwerkkonfiguration |
| system/udev/ | [HUDIY udev](../apps/hudiy/integration/udev/) | Gerätezugriff |
| übriges system/ | [vehicle/platform/](../vehicle/platform/) | Boot-Hardware und Strombefehle |
| systemd/ und weather-sync.service an Wurzel | [deployment/](../deployment/) | System-/Benutzerdienste und getrennte Dublette |
| scripts/testbench.py | [tools/fis-testbench/](../tools/fis-testbench/) | ZeroMQ-Test |
| recovery/, docs/, übrige tools/ | unverändert | Referenzen, Dokumentation und Diagnose |

## Bewusst verbleibende alte Pfade

- `launcher/`, ausführbare Dateien unter `scripts/` und die beiden Python-Helfer an der Wurzel enthalten nur Weiterleitungen. Die Implementierung steht im Fachordner. Der bislang verwendete Aufruf bleibt gültig.
- `scripts/features.conf` ist weiterhin die führende veränderliche Laufzeitkonfiguration. Die Integrationslogik liest sie über den alten Startkontext.
- `scripts/hudiy_api/` bleibt ausschließlich lokal und wird ausdrücklich von Git ausgeschlossen. Der vom Betreiber gemeldete unversionierte Bestand wird weder eingelesen noch verschoben oder veröffentlicht.
- `hudiy/api_files/` ist bereits veröffentlichter Altbestand mit ungeklärten Rechten. Er bleibt unverändert am bisherigen Ort; die Neuordnung kopiert diese Dateien nicht in die neuen Anwendungsordner.

Mira-Core-Integration enthält weiterhin einen Monolithen mit Vehicle-, FIS-, HUDIY- und Kameraanteilen. Eine interne Codezerlegung wäre eine eigene Funktionsänderung. Die neue Ordnerstruktur behauptet keine Trennung, die der Code noch nicht hat.
