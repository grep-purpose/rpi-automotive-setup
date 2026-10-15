# Umstellung und Rückweg

[Startseite](../README.md) · [Pfadzuordnung](PFADZUORDNUNG.md)

## Was aus den Pi-Ausgaben bekannt ist

Der Betreiber hat am 15.10.2026 bestätigt: Der Checkout steht auf main und zeigte ausschließlich scripts/hudiy_api/ als unversionierten Bestand. Der Launcher wird in der installierten Unit sowie im systemweiten labwc-Autostart unter /home/pi/rpi-automotive-setup/launcher/boot_launcher.py referenziert. Cron startet read_from_canbus.py unter /home/pi/rpi-automotive-setup/scripts/.

Die abgefragten Pfade unter /home/pi/rns-e_can, /home/pi/audi-rns-overlay, /home/pi/hudiy_client, /home/pi/dis_client sowie /home/pi/rnse_ops_switcher.py und /home/pi/scripts/pi_control.py wurden auf sich selbst aufgelöst: keine symbolischen Verknüpfungen in den Checkout. Hardlinks, Bind-Mounts und weitere nicht abgefragte Aufrufe sind damit nicht ausgeschlossen. Die Ausgaben belegen installierte Definitionen, nicht deren Aktivzustand.

## Verhalten nach Übernahme

1. Die Implementierungen stehen in den Fachordnern. 27 bisherige ausführbare Einstiegspfade bleiben als Weiterleitungen erhalten.
2. Bei scripts-Python-Einstiegen bleibt __file__ auf dem bisherigen Pfad. Dadurch bleiben scripts/features.conf, scripts/hudiy_api und Logs am bisherigen Ort. Argumente und Exitcodes werden unverändert durchgereicht. Die echte Datei wird im selben Prozess ausgeführt.
3. Launcher-Weiterleitungen verwenden den neuen Paketpfad, damit die zusammen verschobenen Launcher-/Boot-Ressourcen gefunden werden.
4. Bestehende Units, Cron und labwc müssen für diese Umstellung nicht neu installiert werden. Separate Pi-Installationskopien werden nicht verändert.
5. HUDIY-Laufzeitdaten bleiben privat und werden von Git ausgeschlossen. Vor dem Update trotzdem privat sichern. Keine API-Ordner mit git add -f aufnehmen.
6. Implementierungen unter mira-core nicht anstelle der dokumentierten alten Einstiege direkt starten: Sie können von ihrem historischen Laufzeitverzeichnis abhängen. Eine spätere Ablösung der Kompatibilität ist ein eigener, am Fahrzeug zu prüfender Schritt.

## Update auf dem Pi – erst nach Übernahme des PR in main

Zuerst eine private Sicherung nach [Recovery](../recovery/README.md) erstellen. Dann im per SSH geöffneten Pi-Terminal:

```bash
cd /home/pi/rpi-automotive-setup
git status --short --branch
git rev-parse HEAD
```

Die ausgegebene Commit-Kennung außerhalb des Repository notieren. Bei Änderungen an versionierten Dateien zuerst deren Sicherung und Zusammenführung klären. Der private HUDIY-Ordner darf vorhanden bleiben. Anschließend:

```bash
git pull --ff-only origin main
python3 tools/check_layout.py
python3 -m unittest discover -s tools/tests -v
```

Nur wenn die Prüfung erfolgreich ist, ist die neue Ablage vollständig vorhanden. Ein erfolgreicher Strukturtest ist noch kein Fahrzeugtest. Laufende Prozesse werden durch git pull nicht automatisch neu gestartet; ein Prozess, der während des Updates startet, könnte einen Zwischenstand sehen. Das Update deshalb im geparkten Fahrzeug und außerhalb eines laufenden Start-/Umschaltvorgangs durchführen. Kein automatischer Reboot oder Dienstneustart gehört zu dieser Änderung.

Danach Launcher, Wechsel Kodi/HUDIY, Tasten, FIS und Parking am Fahrzeug prüfen. Bei Fehlern zuerst Logs sichern, nicht mehrere alternative Dienste einschalten.

## Rückweg

Bei einer erforderlichen Rückkehr zuerst neue lokale Änderungen und private Laufzeitdaten sichern. Im geparkten Fahrzeug, außerhalb eines Start-/Umschaltvorgangs, kann Git den vorher notierten Stand wieder auschecken. `DEINE_NOTIERTE_COMMIT_KENNUNG` durch diese Kennung ersetzen:

```bash
cd /home/pi/rpi-automotive-setup
git status --short
git switch --detach DEINE_NOTIERTE_COMMIT_KENNUNG
```

Kein `--force` ergänzen: Falls Git wegen lokaler Änderungen abbricht, zuerst deren Sicherung/Zusammenführung klären. Der private Ordner bleibt am unveränderten Pfad. „Detached HEAD“ bedeutet hier nur, dass genau der gesicherte Commit ausgecheckt ist. Laufende Programme werden dadurch nicht automatisch neu gestartet. Für einen späteren erneuten Versuch führt `git switch main` zurück zum lokalen main-Branch. Kein git reset --hard oder git clean verwenden.

Der historische Boot-Installer wurde ausschließlich auf die neuen echten Launcher-/Asset-Pfade angepasst. Vor der Neuordnung erzeugte Installer-Backups passen zu den alten Pfaden; sie mit dem damaligen Installer/Checkout wiederherstellen. Nicht den neuen Installer auf alte Backup-Manifeste anwenden.

## Umfang der Prüfung

Geprüft wurden Dateiinventar, erhaltene Ausführungsrechte, Weiterleitungsziele, Python-Argumente/Exitcodes und Datenkontext mit ungefährlichen Testprogrammen, Launcher-Ressourcenpfade sowie relative Dokumentationslinks. Der Shell-Weiterleitungstest wurde unter Windows mangels Bash übersprungen; der obige Testbefehl führt ihn auf einem Pi mit Bash aus. Produktive Python-Programme werden dabei nicht importiert oder ausgeführt. Es fand kein Pi-/Fahrzeug-/Boot-Test statt.
