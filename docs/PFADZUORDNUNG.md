# Navigation und vorgeschlagene Pfade

[Startseite](../README.md) · [Architektur](ARCHITEKTUR.md)

**Nur Vorschlag, kein Umzug.** Alle Verweise führen zu heutigen Dateien. Zielpfade existieren noch nicht zwingend. Ganze Verzeichnisse gelten rekursiv, sofern eine speziellere Zeile Vorrang hat. Der Dateiname bleibt unter dem Zielbereich erhalten. Verzeichnisgruppen erfassen auch Bilder, Vorlagen und sonstige Begleitdateien.

Mira Core bezeichnet hier gemeinsame Bedienung, FIS und Medienkoordination. Kodi-gebundene Adapter bleiben bei Kodi. Vehicle trägt Bus/Signale/Stromversorgung. Parking bleibt ein gemeinsamer Bereich für Kamera, Video und OPS/PDC.

| Heutiger Pfad / Gruppe | Vorgeschlagener Bereich | Funktion / Abhängigkeit |
|---|---|---|
| [kodi/](../kodi/) | apps/kodi/ | Oberfläche, Add-ons, Einstellungen; Struktur zunächst erhalten |
| kodi/addons/skin.estuary.custom/, kodi/skin.estuary.custom/ und kodi/skin/ | apps/kodi/ui/ mit getrennten Unterordnern | Parallele Skin-Ablagen nicht blind zusammenführen |
| kodi/userdata/, kodi/keymaps/, kodi/playlists/, XML an kodi/-Wurzel | apps/kodi/config/ mit getrennten Herkunftsordnern | Doppelte Namen und Versionsstände erst vergleichen |
| kodi/scripts/music_status.py | apps/kodi/adapters/media/ | Globale Medienaufgabe, aber xbmc-Abhängigkeit |
| kodi/addons/service.rnse.metadata/ | apps/kodi/addons/service.rnse.metadata/ | UDP-Medienempfang und FIS-Metadaten |
| kodi/userdata/rnse_media_router.py | apps/kodi/adapters/media/ | Kodi-Radio-/Medienbefehle |
| [hudiy/](../hudiy/) ohne api_files/ | apps/hudiy/integration/ | Adapter, Start und Menükonfiguration |
| hudiy/api_files/ | **Kein Veröffentlichungs-/Umzugsziel vor Rechteklärung** | Bereits vorhandener Bestand; keine neue SDK-Übernahme |
| [can/rns-e_can/can_handler.py](../can/rns-e_can/can_handler.py) | vehicle/can/ | CAN/ZeroMQ-Gateway; Parking-Sperre als Querverbindung dokumentieren |
| can/rns-e_can/can_base_function.py | vehicle/power-time/ | TV-Präsenz, Zeit, Shutdown und Stromhaltung |
| can/rns-e_can/can_keyboard_control.py | mira-core/input/ | Tasten, FIS- und Medienkommandos |
| [dis_client/](../dis_client/) | mira-core/fis/ | DDP, DisplayEngine, Seiten und Symbole zusammenhalten |
| [scripts/read_from_canbus.py](../scripts/read_from_canbus.py), scripts/features.conf | mira-core/integration/ | Monolith vorerst zusammenhalten; Vehicle/HUDIY/FIS/Parking-Anteile nicht durch Umbenennen „trennen“ |
| recovery/live-config/can/read_from_canbus.py | recovery/snapshots/can/ | Separate Sicherung, kein produktiver Ersatz |
| [can/audi-rns-overlay/](../can/audi-rns-overlay/), scripts/rnse_ops_switcher.py | parking/overlay/ und parking/video-switch/ | **Eine Parking-Kette**; Api_pb2-Zugehörigkeit/Verwendung offen |
| scripts/pi_control.py | mira-core/control/ | HTTP, Audio, Strom und Kamerabefehl; mehrere Fachbereiche |
| scripts/nav_icon_decoder.py | mira-core/fis/tools/ | Navigationssymbol-Helfer |
| scripts/input_watchdog.py | mira-core/input/monitoring/ | Tastenüberwachung |
| scripts/can_health_monitor.py | vehicle/can/monitoring/ | CAN-Diagnose |
| scripts/mira_usb_manager.py, scripts/mira-usb-mount, config/usb/ | mira-core/media/usb/ | Mount, Index, iPod; Indexziel derzeit Kodi |
| scripts/dac-fix.sh, scripts/rnse-a2dp-watch.sh, scripts/rnse-bluetooth-autoconnect.sh, config/audio/ | mira-core/media/audio/ | Audio und Bluetooth |
| scripts/mira-screenshot, scripts/mira_screenshot_queue.py, scripts/mira_telegram_send.py, assets/ | mira-core/diagnostics/screenshots/ | Aufnahme, Warteschlange, Versand und Ton; private Versandkonfiguration extern |
| scripts/weather/ | apps/kodi/weather/ | Wetter-Ortsumschaltung |
| update_radar.py, test_gps_coords.py | apps/kodi/weather/tools/ | Radar/GPS-Helfer; Radar-Dubletten separat vergleichen |
| scripts/testbench.py | tools/fis-testbench/ | ZeroMQ-Test, kein vollständiger CAN-Simulator |
| [tools/](../tools/) | tools/ | Diagnose/Bridges; vorhandene Unterteilung behalten |
| [launcher/](../launcher/), [boot/](../boot/) | platform/boot-launcher/ mit getrennten Unterordnern | Launcher, Animation, Übergang und Messung; Varianten erhalten |
| config/labwc/ | platform/session/labwc/ | Desktopstart, nicht HUDIY-Anwendungscode |
| system/config.txt, system/network/ | vehicle/platform/ | Boot-/Bus-Hardwarekonfiguration mit Display-/Audio-Querverweisen |
| system/udev/99-hudiy.rules | apps/hudiy/integration/udev/ | Gerätezugriff für HUDIY |
| system/rnse-power, system/rnse-power.sudoers | vehicle/power/ | System-Strombefehle und Berechtigung |
| [vga-edid/](../vga-edid/) | platform/display/ | EDID, Sync-Combiner und Gehäuse; keine automatische Zuordnung zum Parking-Zwischengerät |
| [systemd/](../systemd/) | deployment/systemd/ | Startdefinitionen zentral; fachlicher Besitzer siehe nächste Tabelle |
| weather-sync.service an Wurzel | deployment/systemd/variants/root/weather-sync.service | Dublette bis zum Vergleich separat bewahren |
| [recovery/](../recovery/) | recovery/ | Gesicherte Zustände und Wiederherstellung bleiben getrennt |
| README.md, docs/, .gitignore | bisheriger Pfad | Einstieg, Dokumentation und Git-Regeln |

## Fachlicher Besitzer der Startdefinitionen

Die Trennung system/systemd und user bleibt erhalten; sie bezeichnet unterschiedliche Startkontexte.

| Units / Gruppe | Fachlicher Bereich |
|---|---|
| can_handler, can_base_function, can0-setup, can-health-monitor, vcan0 | Vehicle |
| can_keyboard_control, input-watchdog, dis_toplines | Mira Core: Eingabe/FIS |
| dark_mode_api, hudiy_data_api | HUDIY-Adapter |
| audi-camera-overlay, rns-overlay, rnse-ops-switcher | **Parking gemeinsam** |
| rnse-a2dp-watch, rnse-bluetooth-autoconnect, dac-routing, mira-usb-* | Mira Core: Medien |
| weather-sync, radar-updater, waipu-proxy | Kodi |
| mira-screenshot-upload | Mira Core: Diagnose |
| rpi-automotive-launcher, cpu-performance | Boot/Plattform |

## Regeln für eine spätere tatsächliche Migration

1. Aktive Kopien auf dem Pi ermitteln; Git-Datei ist nicht automatisch die installierte Datei.
2. Doppelte Kodi-/Radar-/Boot-Dateien getrennt vergleichen und eine führende Quelle festlegen.
3. Absolute Pfade in Units, Cron, Shell, Python, Kodi-XML und HUDIY-Menüs gemeinsam ändern. Relative Imports und features.conf neben read_from_canbus berücksichtigen.
4. SDK-/API-Rechte klären. Keine proprietären HUDIY-Dateien in neue Zielordner kopieren.
5. Je Funktionskette mit Sicherung und Rollback migrieren. Parking als Gesamtsystem abnehmen.

Der Monolith read_from_canbus bleibt vorerst ein Integrationsmodul. Eine echte Aufteilung seiner Funktionen wäre eine gesonderte Codeänderung mit Tests, nicht bloß ein Dateiumzug.
