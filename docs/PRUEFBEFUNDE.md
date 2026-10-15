# Prüfbefunde und offene Fragen

[Startseite](../README.md) · [Parking](PARKING.md) · [Recovery](../recovery/README.md)

Basis: main / 9abba0b2790ebfdeee3efe1a1fbe9b17ea250104, geprüft am 15.10.2026. Statische Prüfung von Einstiegspunkten, Funktionspfaden, Units, Cron und Konfiguration. Kein vollständiger Funktionstest aller Add-ons oder externer Dienste.

## Korrekturen gegenüber der bisherigen Haupt-README

| Bisherige Darstellung | Befund und korrigierte Einordnung |
|---|---|
| read_from_canbus ist ein Logging-/Diagnosewerkzeug | [Code](../mira-core/integration/read_from_canbus.py) enthält CAN-Senden, FIS, HUDIY, App-Wechsel, Kamera und Fernsteuerung; produktive, übergreifende Integration |
| can_base_function liest Basissignale | [Code](../vehicle/power-time/can_base_function.py) enthält auch TV-Simulation, Zeitsetzung, Shutdown/Watchdog und GPIO-Stromhaltung |
| hudiy_data reicht Fahrzeugdaten an HUDIY weiter | [Code](../apps/hudiy/integration/hudiy_data.py) extrahiert HUDIY-Medien/Navigation/Telefon und veröffentlicht sie |
| dis_display/dis_service sind nur obere FIS-Zeilen | [DisplayEngine](../mira-core/fis/dis_display.py) und [DIS Service](../mira-core/fis/dis_service.py) implementieren Seiten und DDP-Zeichenbefehle; separater Toplines-Einstieg fehlt |
| can_daemon überwacht Status, Api_pb2 ist seine Kommunikation | [Daemon](../parking/overlay/can_daemon.py) rendert GStreamer/Cairo-Kamerabild und PDC; importiert Api_pb2 nicht |
| testbench ist CAN-Frame-Simulator | [Code](../tools/fis-testbench/testbench.py) simuliert ZeroMQ-Nachrichten und Zeichenempfang, keinen vollständigen SocketCAN-Fahrzeugbus |
| EDID-Installer unter vga-edid/install_edid.sh | Tatsächlich [vga-edid/edid_installer/install_edid.sh](../platform/display/edid_installer/install_edid.sh) |
| Kamera / Video / OPS lose Einzelkomponenten | Gemeinsame Parking-Kette einschließlich Handler-Sendesperre und externer Hardware; [Detailbefunde](PARKING.md) |

## Offene oder widersprüchliche Stellen

| ID | Befund mit Quelle | Bedeutung / nächster Beleg |
|---|---|---|
| P1 | Parking-Trigger 0x359 vs. 0x351; Lenkwinkel 0x0C0; externe 0x6DA-Daten | Passive Fahrzeugaufzeichnung und Zwischengerät-Dokumentation nötig |
| P2 | Switcher nimmt Pi-Bild weg, Overlay zeichnet auf Pi | Tatsächlichen Video-/Hardwarepfad klären; keine garantierte gemeinsame Funktion |
| P3 | Zwei Overlay-Units, pi_control auf Port 44408, weitere Kamera in read_from_canbus | Installierte/aktive Prozesse und Gerätebelegung prüfen |
| P4 | pi_control sendet toggle_revcam_no_lines, handle_client unterstützt es nicht | Manueller Kameraweg im geprüften Stand unvollständig |
| F1 | [dis_toplines.service](../deployment/systemd/dis_toplines.service) startet fehlende dis_toplines.py | Kein vollständiges Recovery dieses Dienstes aus Git möglich |
| F2 | dis_display/dis_service vorhanden, passende gleichnamige Units fehlen; zweiter FIS-Pfad in read_from_canbus | Tatsächliche FIS-Zuständigkeit und Startweg erheben |
| C1 | /home/pi/config.json mehrfach erforderlich, nicht eingecheckt | Lokal sichern; bereinigtes Schema später ableiten, keine Werte erfinden |
| B1 | [config/labwc/autostart](../platform/session/labwc/autostart) startet HUDIY, Recovery system-autostart startet Launcher; zusätzlich systemd-Launcher | Aktiven Startweg prüfen, Doppelstarts vermeiden |
| B2 | Mehrere Boot-Konfigurationen und Launcher-Kopien | Boot-Paket ist versionsgebunden; keine pauschale Installation oder Überschreibung |
| W1 | weather-sync doppelt, Radar-Skripte mehrfach, zusätzliche User-Unit und Cron-Helfer | Tatsächlich aktive Wetterquelle nicht aus Dateinamen ableitbar |
| H1 | Herkunftsnotiz behauptete keine HUDIY-Quelldateien im Repo, hudiy/api_files/common ist vorhanden | Notiz korrigiert; Lizenz-/Herkunftsklärung weiterhin offen |
| T1 | testbench sendet CAN_0x5C3; Handler erzeugt CAN_5C3 | Kein Beleg für austauschbare Test- und Produktivnachrichten; Abonnenten gesondert prüfen |
| A1 | audi-camera-overlay/rns-overlay erwarten html; Daemon erwartet car_top.png | Ressourcen fehlen am angegebenen Repository-Ort; lokale Installation prüfen |

## Bestehende Spezial-READMEs

- [Boot-Animation](../platform/boot/mira-animation/README.md): beschreibt ein versionsgebundenes Installationspaket mit Sicherung/Restore. Hardwaretest wurde dort bereits ausdrücklich ausgeschlossen. Ergänzter Hinweis grenzt es von der allgemeinen Recovery ab.
- [VGA-Hardware](../platform/display/README.md): beschreibt den Sync-Combiner. Elektrische Eignung, Testtabellen und tatsächliche Fahrzeugverdrahtung sind durch diese Codeprüfung nicht neu bestätigt.
- [EDID-Installer](../platform/display/edid_installer/README.md): beschreibt Änderungen an Boot-Konfiguration und Kernel-Kommandozeile, keine Parking-Steuerung.
- [Gehäuse](../platform/display/3d_print_case/README.md): mechanische Referenz, keine Software-Startanleitung.

## Freigabekriterien für spätere Umbauten

Vor einer produktiven Pfadänderung: aktive Dateien/Units erfassen, lokale Konfiguration sichern, jeden absoluten Pfad und Import zuordnen, HUDIY-Rechte klären und Rollback festlegen. Erst danach jeweils eine Funktionskette umstellen und am Pi prüfen. Die anschließende Strukturänderung verlagert die Dateien und erhält die bekannten alten Startpfade über Weiterleitungen. Siehe [Umstellung](UMSTELLUNG.md).
