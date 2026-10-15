# Globale Mira-Core-Funktionen

| Ordner | Aufgabe |
|---|---|
| [input](input/) | Globale Tasten und Eingabeüberwachung |
| [fis](fis/) | Kombiinstrument, DDP und FIS-Seiten |
| [media](media/) | USB, Audio und Bluetooth |
| [integration](integration/) | Übergreifendes CAN-/FIS-/HUDIY-Skript und sein Decoder |
| [control](control/) | HTTP-Steuerung |
| [diagnostics](diagnostics/) | Screenshots und Versandwarteschlange |

Die Installationspfade auf dem Pi bleiben bestehen. **Skripte, die bisher unter scripts/ gestartet wurden, weiter über diese Kompatibilitätseinstiege starten.** Nur so bleiben ihr ursprünglicher Daten-/API-Kontext und die Laufzeitkonfiguration erhalten. Die neuen Dateien sind die bearbeitbaren Implementierungen, keine pauschal direkt ausführbaren Installationen.

Bei einer separaten Installation die echte Implementierung samt benötigten Nachbardateien verwenden. Eine Kompatibilitätsdatei nicht allein nach /home/pi oder /usr/local kopieren: Ihr relativer Verweis benötigt den vollständigen Repository-Baum.

[Umstellung](../docs/UMSTELLUNG.md) · [Startseite](../README.md)
