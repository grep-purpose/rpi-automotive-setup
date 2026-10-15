# Bestehende Startpfade und private Laufzeitdaten

Die Implementierungen stehen jetzt in Fachordnern; diese kleinen Dateien halten bisherige Cron-, systemd- und andere Aufrufe funktionsfähig. Python-Weiterleitungen erhalten insbesondere den alten __file__-Kontext, damit features.conf, lokale HUDIY-API und Datenpfade unverändert gefunden werden.

**features.conf bleibt hier die führende Konfiguration. hudiy_api/ bleibt lokal und wird nicht veröffentlicht.** Diesen Ordner und die Weiterleitungen nicht löschen. Nicht die Weiterleitungen, sondern die im Dateikopf genannten Implementierungen bearbeiten.

[Zuordnung](../docs/PFADZUORDNUNG.md) · [Umstellung](../docs/UMSTELLUNG.md)
