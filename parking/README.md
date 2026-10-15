# Parking – ein zusammenhängendes System

- [overlay](overlay/): Kameraaufnahme, Führungslinien und OPS/PDC-Darstellung.
- [video-switch](video-switch/): Videoquellenumschaltung über Pi-Display-Abschaltung.
- [CAN-Handler](../vehicle/can/can_handler.py): zusätzliche Sperre von TV-Präsenz-Sendeaufträgen.
- [Startdefinitionen](../deployment/systemd/): audi-camera-overlay, rns-overlay und rnse-ops-switcher.

Die vollständige Kette, unterschiedlichen CAN-Trigger und das noch ungeklärte externe Zwischengerät stehen in [Parking](../docs/PARKING.md). Die Ordnerneuordnung behebt keine dieser funktionalen Unklarheiten.

[Startseite](../README.md)
