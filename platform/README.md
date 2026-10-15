# Pi-Plattform: Boot, Launcher und Display

- [boot](boot/): Animation, Übergänge und Boot-Diagnose.
- [launcher](launcher/): Auswahl zwischen Kodi und HUDIY.
- [display](display/): EDID, VGA-Sync-Combiner und Gehäuse.
- [session](session/): Desktop-/labwc-Konfiguration.

Alte Launcher-Aufrufe werden weiter unterstützt. Der versionsgebundene Boot-Installer zielt jetzt auf die echten Launcher-Dateien in platform/launcher. Seine bisherigen SHA-/Hardware-Prüfungen bleiben aktiv. Bereits vor dieser Neuordnung angelegte Installer-Backups verwenden alte Zielpfade: Dafür die damalige Installer-Version zusammen mit dem damaligen Repository-Stand verwenden, nicht den neuen Installer auf alte Backups anwenden.

[Startseite](../README.md)
