# Startwege, Laufzeitpfade und Abhängigkeiten

[Startseite](../README.md) · [Architektur](ARCHITEKTUR.md)

Alle Einträge sind **vorhandene Startdefinitionen**, kein Nachweis aktiver Dienste. Repository-Pfad und Installationspfad unterscheiden sich. Systemdienste werden mit systemctl untersucht, Benutzerdienste als pi mit systemctl --user. Requires fordert einen Dienst an, After ordnet den Start und BindsTo koppelt den Lebenszyklus; After allein startet keinen anderen Dienst.

## Systemdienste

Quellen: [systemd/](../deployment/systemd) und [systemd/system/](../systemd/system).

| Unit | Programm / Laufzeitort | Abhängigkeit oder Prüfpunkt |
|---|---|---|
| can0-setup | ip link, 100000 bit/s | Parallel zu system/network/80-can.network vorhanden; Before nennt auch nicht vorhandene dis_service.service |
| can_handler | /home/pi/rns-e_can/can_handler.py | An can0-Gerät gebunden; braucht /home/pi/config.json |
| can_base_function | /home/pi/rns-e_can/can_base_function.py | Requires, After und BindsTo can_handler |
| can_keyboard_control | /home/pi/rns-e_can/can_keyboard_control.py | Wants/After can_handler; pi, Gruppe input |
| dark_mode_api | /home/pi/hudiy_client/dark_mode_api.py | Requires/After can_handler; zusätzliche HUDIY-API nötig |
| hudiy_data_api | /home/pi/hudiy_client/hudiy_data.py | Requires/After can_handler; liest HUDIY-Ereignisse |
| dis_toplines | /home/pi/dis_client/dis_toplines.py | Requires/After/BindsTo hudiy_data_api; Zieldatei fehlt |
| audi-camera-overlay | /home/pi/audi-rns-overlay/can_daemon.py | HTTP 44408 im ExecStartPre; kein CAN-/Wayland-Bereitschaftswarten |
| rns-overlay | derselbe can_daemon | Startet HTTP 44408 und Python in Shell; doppelte Variante |
| rnse-ops-switcher | /home/pi/rnse_ops_switcher.py | Wants/After can0-Gerät; keine Kopplung mit Overlay |
| rpi-automotive-launcher | /home/pi/rpi-automotive-setup/launcher/boot_launcher.py | Wartet auf /run/user/1000/wayland-0; zusätzlich labwc-Startwege vorhanden |
| can-health-monitor | Repo scripts/can_health_monitor.py | root; After CAN-Handler und Tasten |
| input-watchdog | Repo scripts/input_watchdog.py | root; Wants/After CAN-Handler und Tasten |
| rnse-bluetooth-autoconnect | /usr/local/bin/rnse-bluetooth-autoconnect.sh | Einmaliger Start nach Bluetooth und user@1000 |
| rnse-a2dp-watch | /usr/local/bin/rnse-a2dp-watch.sh | Bluetooth-Diagnose |
| weather-sync | /home/pi/.kodi/userdata/live_sync_worker.py | Identische Unit zusätzlich an Repository-Wurzel |
| waipu-proxy | /home/pi/.kodi/userdata/scripts/waipu_proxy.py | Netzwerk; Kodi-bezogener Proxy |
| cpu-performance | Shell setzt CPU-governor | Hardware-/Systemoptimierung |
| vcan0 | ip/modprobe | Virtueller Bus für getrennte Tests; kein Beleg für Fahrzeugbetrieb |
| mira-usb-index | /home/pi/mira_usb_manager.py | Timer: 30 s nach Boot, 30 s nach letzter Inaktivität |
| mira-usb-mount@ | /usr/local/sbin/mira-usb-mount | Mount-Helfer, Instanzparameter bezeichnet Gerät |

Die USB-/iPod-Ergänzungen liegen unter [config/usb/](../mira-core/media/usb/deployment): Eject-/Rearm-Units, udev-Regel, Root-Helfer und fstab-/sudoers-Beispiele. Beispiele sind keine bereits installierte Konfiguration.

## Benutzerdienste

Quellen: [systemd/user/](../systemd/user).

| Unit | Aufruf | Hinweis |
|---|---|---|
| dac-routing | /home/pi/.config/dac-fix.sh | Nach PipeWire/WirePlumber; Quelle scripts/dac-fix.sh |
| radar-updater | /home/pi/update_radar.py, Schleife alle 900 s | Mehrere Radar-Skriptkopien vorhanden; Zielversion offen |
| mira-screenshot-upload | /usr/local/lib/mira/mira_screenshot_queue.py process | Timer nach 1 min und jede Minute; externer Versand, private Konfiguration nötig |

## Cron, Desktop und Kodi

Die [gesicherte pi.crontab](../recovery/live-config/cron/pi.crontab) enthält zwei @reboot-Einträge:

- /home/pi/scripts/pi_control.py, mit Python aus /home/pi/.venv-canbus/.
- /home/pi/rpi-automotive-setup/scripts/read_from_canbus.py, ebenfalls diese Umgebung; Arbeitsordner /home/pi/scripts.

read_from_canbus lädt features.conf **neben seiner eigenen Datei**, nicht aus dem Cron-Arbeitsordner. Die Recovery-Kopie unter live-config/can/ ist eine separate Sicherungsvariante; ihre Existenz macht sie nicht zur aktiven Quelle.

[config/labwc/autostart](../platform/session/labwc/autostart) startet HUDIY direkt nach 3 Sekunden. [Recovery system-autostart](../recovery/live-config/labwc/system-autostart) startet stattdessen den Launcher mit exec. Im gespeicherten Benutzer-autostart steht nur ein Verweis auf den zentralen Start. Weitere Varianten: boot/mira-bridge/ und boot/mira-diagnostics/. Der Cursor-Block hinter exec wird bei erfolgreichem exec nicht mehr ausgeführt.

[kodi/userdata/autoexec.py](../apps/kodi/userdata/autoexec.py) enthält nur einen auskommentierten Wetterstart; es ist kein Beleg für einen aktiven Wetterdienst. Kodi-Add-ons haben eigene Einstiegspunkte in addon.xml. Das Medien-Add-on ist deshalb kein fehlender systemd-Dienst.

## Schnittstellenkarte

| Schnittstelle | Sender → Empfänger | Prüfung |
|---|---|---|
| ZeroMQ publish_address / send_address | CAN-Handler ↔ Abonnenten/Sender | Werte aus fehlender /home/pi/config.json |
| ZeroMQ hudiy_publish_address / dis_draw | HUDIY-Daten → DisplayEngine → DIS-Service | Werte aus config.json; HUDIY-Datenadapter hat IPC-Fallback |
| TCP 44405 / WebSocket 44406 | HUDIY-Datenadapter ↔ HUDIY | Externe Anwendung erforderlich |
| TCP 23456 | Tasten/pi_control → read_from_canbus | FIS/App-Wechsel vorhanden; manueller Kamerabefehl fehlt im Empfänger |
| UDP 23457 | Tasten → Kodi Metadaten-Add-on | Verteilt Medienbefehle an Kodi-Skripte |
| HTTP 44408 | pi_control oder Overlay-Webserver | Konkurrenz bei gleichzeitiger Aktivierung |
| HTTP 44409 | HUDIY-Menü → read_from_canbus | Lokaler Kodi-Wechsel-Server |
| /dev/video0 | Kameracode → Capture-Gerät | Mehrere mögliche Besitzer, keine zentrale Vergabe |
| /run/user/1000/rnse_active_app | Launcher → Medienlogik | Fest eingetragene Benutzer-ID; nicht universell übertragbar |

Vor Installation oder Umzug müssen diese Laufzeitpfade und Rechte auf dem Pi geprüft werden. Es gibt in diesem PR bewusst keine Enable-/Restart-/Installationsbefehle.
