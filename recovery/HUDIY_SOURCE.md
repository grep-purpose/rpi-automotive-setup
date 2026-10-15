# HUDIY – Herkunft und Wiederherstellungsgrenzen

[Startseite](../README.md) · [Recovery](README.md)

## Gesicherte Herkunftsangaben

Die frühere Notiz nennt eine bestehende Mira-Installation, Branch main und Quellstand fc5b480 sowie die Einzelstände Api_pb2.py: fc5b480, Client.py: 303a9f5, Message.py: ef3b1e9. Eine eindeutig zugehörige externe Repository-Adresse und die Weiterverbreitungsbedingungen sind damit noch nicht belegt. Diese Angaben wurden in der aktuellen Prüfung nicht unabhängig bestätigt.

Als lokaler Quellpfad war /home/pi/rpi-automotive-setup/scripts/hudiy_api/ angegeben. Das ist ein Laufzeit-/Installationshinweis, kein hier vollständig vorhandener Quellordner.

## Korrektur zum Repository-Bestand

Im geprüften main-Stand 9abba0b liegen bereits Dateien unter hudiy/api_files/common/ (Api.proto, Api_pb2.py, Client.py, Message.py). Die frühere pauschale Aussage, HUDIY-Quelldateien seien nicht übernommen worden, war deshalb unzutreffend.

Die Existenz dieser Dateien ist **kein Nachweis einer Veröffentlichungserlaubnis**. Es werden mit dieser Strukturänderung keine weiteren HUDIY-Dateien übernommen, vervielfältigt oder in neue Produktordner verschoben. Rechte und Herkunft des vorhandenen Bestands bleiben gesondert zu prüfen; eine mögliche Bereinigung wäre eine eigene Änderung.

## Wiederherstellung

Die Startskripte erwarten eine separat installierte Anwendung unter /home/pi/.hudiy/share/. Dieses Repository ersetzt weder deren Installation noch Lizenz oder Zugang. Benötigt werden die rechtmäßig verfügbare Bezugsquelle, passende Version und lokale private Sicherung. Bis diese Punkte geklärt sind, gibt es keine vollständige HUDIY-Neuinstallationsanleitung aus diesem Repository.
