# MIRA boot integration

> Einordnung: versionsgebundenes Boot-Paket, keine allgemeine Neuinstallation.
> Die Aussagen zur damals untersuchten Umgebung sind historischer Kontext und
> keine Bestätigung des heute laufenden Pi. Zuerst [Startwege](../../docs/STARTWEGE.md)
> und [Recovery](../../recovery/README.md) lesen. Der unten genannte Ordner
> `/home/pi/mira-install` muss separat vorhanden sein; ein Git-Clone legt ihn nicht an.
> Der Git-Abschnitt dokumentiert den ursprünglichen Arbeitsablauf, nicht den
> notwendigen Schritt zur Nutzung dieser Dokumentation. Keine pauschale Aktivierung
> weiterer Launcher-/Autostartvarianten.

Prepared for the uploaded 800-line PyQt5 launcher, Debian 12, Raspberry Pi 4,
kernel rpi-v8, labwc/LightDM, and active automatic initramfs8 loading.

The original HTML canvas is rendered into 156 PNG images at 800x480 / 15 fps.
Waves retain their 5.2-second period; border rotation and background glow use
10.4 seconds so the complete image loop repeats seamlessly. Plymouth fades in
over approximately 1.2 seconds. The same frames cover the launcher's first
1.2 seconds, fading to the existing menu in the last 0.3 seconds. Any key
dismisses this short overlay. It does not replay after returning from Kodi/Hudiy.
There is no browser, password store, added service or autostart change.
LightDM's existing Plymouth shutdown behavior is unchanged: a black gap and
animation phase restart at the desktop handoff are possible.

Frames are loaded on demand, not all decoded into RAM. Plymouth updates at
15 fps based on its nominal 30 Hz refresh callback. Slow hardware can reduce
playback speed. The Qt side uses elapsed time and a six-frame cache.

## Install on the inspected Pi

    sudo python3 /home/pi/mira-install/install.py

The installer refuses a different launcher SHA256, an existing MIRA installation,
missing script plugin, insufficient space, or a mismatched kernel initrd.
It backs up the launcher, Plymouth configuration, kernel initrd and initramfs8
under /var/backups/mira-boot. It regenerates only the running kernel's initrd,
checks the firmware copy and required files, and restores the old files on an
installation exception. It does not reboot. Do not power off during installation.
After a failed install, leave the output for diagnosis; a rerun intentionally
refuses any newly created existing directories instead of overwriting them.

## Restore over SSH

    sudo python3 /home/pi/mira-install/install.py restore
    sudo reboot

Reconnect from Windows Terminal: ssh pi@192.168.0.59
Restoration leaves repository assets and the inactive theme in place for review.
If the Pi cannot boot, copy the backed-up firmware initramfs8 from the recovery
folder on Windows to initramfs8 on the SD card's boot partition. The separately
saved config.txt is also available if boot configuration needs restoring.

## Git (after successful installation)

    cd /home/pi/rpi-automotive-setup
    git add -- launcher/boot_launcher.py launcher/mira_splash.py boot/mira-animation
    git diff --cached --stat -- launcher/boot_launcher.py launcher/mira_splash.py boot/mira-animation
    git commit -m "Add MIRA Plymouth animation and launcher transition" -- launcher/boot_launcher.py launcher/mira_splash.py boot/mira-animation
    git push

## Validation scope

Local: rendered frames, dimensions, loop continuity, Python syntax and launcher
patch scope. No Pi boot, Plymouth execution, or PyQt5/Wayland hardware test has
been performed by the author. Installer checks are prerequisites, not proof of
a successful visual boot. Inspect the first reboot on the RNS-E.
