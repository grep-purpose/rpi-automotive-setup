# Recovery: zuerst sichern und den tatsächlichen Zustand erfassen

[Startseite](../README.md) · [Startwege](../docs/STARTWEGE.md) · [Prüfbefunde](../docs/PRUEFBEFUNDE.md)

Git allein reicht derzeit nicht für eine vollständige Neuinstallation. Es fehlen unter anderem /home/pi/config.json, einzelne referenzierte Programme/Ressourcen und die bestätigte externe HUDIY-Bezugsquelle. Dieser Leitfaden erklärt sichere Bestandsaufnahme und die Grenzen der Wiederherstellung; er verspricht kein getestetes Komplett-Recovery.

## 1. Von Windows verbinden

Im **Windows Terminal / PowerShell** die Adresse anpassen; die Adresse hier ist ein Platzhalter:

```powershell
ssh pi@DEINE-PI-IP
```

Nach der Anmeldung werden die folgenden Linux-Befehle **auf dem Pi** eingegeben. Annahme ist der im Code verwendete Benutzer pi. Bei anderem Benutzer müssen Pfade und Benutzer-ID geprüft werden.

## 2. Nur lesen: aktive Startwege und Versionen

```bash
hostname
uname -a
cat /etc/os-release
git -C /home/pi/rpi-automotive-setup rev-parse HEAD
git -C /home/pi/rpi-automotive-setup status --short
systemctl --no-pager --failed
systemctl --no-pager list-unit-files 'can*' 'dis*' 'hudiy*' '*overlay*' 'rnse*' 'rpi-automotive*'
systemctl --no-pager status can_handler.service can_keyboard_control.service audi-camera-overlay.service rns-overlay.service rnse-ops-switcher.service
systemctl --user --no-pager list-timers --all
crontab -l
ip -details link show can0
pgrep -af 'can_daemon|rnse_ops_switcher|read_from_canbus|pi_control|boot_launcher|dis_display|dis_service'
ss -lntup
```

„Unit not found“, „inactive“ oder ein fehlender Git-Ordner sind verwertbare Befunde; diese Befehle installieren nichts. list-unit-files zeigt Installation/Aktivierung, status den aktuellen Zustand.

Die tatsächlich installierten Definitionen einschließlich Ergänzungen lesen:

```bash
systemctl cat can_handler.service can_base_function.service can_keyboard_control.service
systemctl cat audi-camera-overlay.service rns-overlay.service rnse-ops-switcher.service
systemctl cat dis_toplines.service rpi-automotive-launcher.service weather-sync.service
cat /etc/xdg/labwc/autostart
cat /home/pi/.config/labwc/autostart
journalctl -b --no-pager -n 150 -u can_handler.service -u audi-camera-overlay.service -u rns-overlay.service -u rnse-ops-switcher.service
```

Ausgaben vor Weitergabe auf private Daten prüfen. Für Parking zusätzlich Modell/Anschlüsse des Zwischengeräts dokumentieren. Dieser Leitfaden sendet keine Testframes und startet keinen Kameraprozess.

## 3. Private Sicherung auf dem Pi

Die Sicherung enthält bewusst auch lokal installierte Programme und möglicherweise Zugangsdaten bzw. proprietäre Bestandteile. **Privat aufbewahren, nicht in GitHub hochladen.** Benötigten freien Speicher vorher mit df -h prüfen.

Auf dem Pi ausführen:

```bash
(
set -e
backup_dir="$HOME/mira-recovery-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$backup_dir"
systemctl list-unit-files > "$backup_dir/system-units.txt"
systemctl --user list-unit-files > "$backup_dir/user-units.txt"
crontab -l > "$backup_dir/pi.crontab" 2> "$backup_dir/crontab-status.txt" || true
git -C /home/pi/rpi-automotive-setup rev-parse HEAD > "$backup_dir/repo-commit.txt"
git -C /home/pi/rpi-automotive-setup diff > "$backup_dir/repo-local.patch"
backup_paths=()
for item in /home/pi /etc/systemd/system /etc/xdg/labwc /etc/udev/rules.d /etc/sudoers.d /etc/fstab /usr/local /boot /var/backups/mira-boot; do
    if [ -e "$item" ]; then
        backup_paths+=("$item")
    else
        printf 'Fehlt: %s\n' "$item" >> "$backup_dir/missing-paths.txt"
    fi
done
sudo tar --acls --xattrs --exclude='mira-recovery-*' -czpf "$backup_dir/private-system.tar.gz" "${backup_paths[@]}"
sudo chown "$(id -u):$(id -g)" "$backup_dir/private-system.tar.gz"
chmod 600 "$backup_dir/private-system.tar.gz"
tar -tzf "$backup_dir/private-system.tar.gz" > "$backup_dir/archive-index.txt"
sha256sum "$backup_dir/private-system.tar.gz" > "$backup_dir/SHA256SUMS"
printf 'Sicherungsordner: %s\n' "$backup_dir"
)
```

Der Block benötigt Bash, protokolliert fehlende Pfade und schließt Ordner namens mira-recovery-* aus. Bei einem Fehler bricht er ab. Während der Sicherung geänderte Dateien können tar mit Fehlerstatus beenden. Eine solche Sicherung ist nicht als vollständig bestätigt anzusehen. Für eine vollständige SD-Kartenwiederherstellung zusätzlich ein Image der ausgeschalteten Karte erstellen; dieses Archiv enthält weder Partitionstabelle noch alle installierten Betriebssystempakete.

## 4. Auf Windows kopieren und prüfen

Ein **neues Windows-PowerShell-Fenster** öffnen; nicht in der SSH-Sitzung ausführen. Adresse und den zuvor ausgegebenen Ordnernamen ersetzen:

```powershell
scp -r pi@DEINE-PI-IP:/home/pi/mira-recovery-JJJJMMTT-HHMMSS .
Get-FileHash .\mira-recovery-JJJJMMTT-HHMMSS\private-system.tar.gz -Algorithm SHA256
Get-Content .\mira-recovery-JJJJMMTT-HHMMSS\SHA256SUMS
```

Die beiden Hashwerte müssen übereinstimmen. Hashgleichheit bestätigt den Transfer, nicht die Vollständigkeit des Backups.

## 5. Wiederherstellung nach Fehlerbild

| Fehler | Vorgehen |
|---|---|
| Nur Dokumentation geändert | Keine Pi-Installation nötig; dieser PR ändert keine Laufzeitdateien |
| Einzelne Konfiguration beschädigt, SSH funktioniert | Betroffenen Startweg bestimmen, lokale Sicherung prüfen, nur diese Datei mit ursprünglichem Eigentümer/Rechten zurückholen; keine komplette Git-Kopie über /home/pi legen |
| Boot-Animation nach Installer geändert | [Versionsgebundene Anleitung](../boot/mira-animation/README.md) und Sicherung unter /var/backups/mira-boot prüfen; Restore betrifft nur dort gesicherte Dateien |
| Pi bootet nicht mehr | SD-Image oder bekannte vollständige Sicherung verwenden; einzelne initramfs-/config-Dateien nur mit passendem Kernel und dokumentiertem Ausgangszustand zurückspielen |
| HUDIY fehlt | Rechtmäßig bezogene Installation separat wiederherstellen; [Herkunftsstatus](HUDIY_SOURCE.md) beachten |
| Parking funktioniert nicht | Gesamtkette nach [Parking](../docs/PARKING.md) prüfen; keine weiteren konkurrierenden Dienste probeweise aktivieren |

Ein pauschaler Restore-Befehl wäre bei den derzeit unklaren produktiven Pfaden nicht belastbar. Vor Rückspielen müssen Quellarchiv, Zielpfad und vorherige aktive Variante eindeutig feststehen. Die unter live-config gesicherten Dateien sind Referenzen, keine automatische Installationsliste.
