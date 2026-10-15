# Startdefinitionen

[systemd](systemd/) enthält Systemdienste sowie die getrennten Unterordner system/ und user/. [variants/root](variants/root/) bewahrt die bisherige weather-sync-Dublette an der Repository-Wurzel.

Die Dateien werden durch git pull nicht automatisch nach /etc oder /usr/local installiert. Bestehende absolute Pi-Installationspfade bleiben unverändert. Die bekannten Repository-Startpfade nutzen weiterhin die Kompatibilitätseinstiege.

[Startwege und Abhängigkeiten](../docs/STARTWEGE.md) · [Startseite](../README.md)
