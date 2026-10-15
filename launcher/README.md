# Kompatibilität für bestehende Launcher-Starts

Die eigentliche Implementierung liegt unter [platform/launcher](../platform/launcher/). Diese Weiterleitungen erhalten die im Fahrzeug eingerichteten systemd-/labwc-Pfade. Python verwendet den neuen Launcher-Verzeichnis-Kontext, sodass Splash, Imports und Startskripte zusammenbleiben.

[Umstellung](../docs/UMSTELLUNG.md)
