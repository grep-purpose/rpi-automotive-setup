#!/bin/sh
set -u

BACKGROUND_READY="/run/user/1000/mira-background-ready"
LAUNCHER_READY="/run/user/1000/mira-launcher-ready"
COUNT=0

while [ "$COUNT" -lt 300 ]; do
    if [ -e "$BACKGROUND_READY" ]; then
        /usr/bin/logger -t mira-plymouth-deferred-deactivate \
          "MIRA background ready; deactivating Plymouth"

        /usr/bin/plymouth deactivate || true
        exit 0
    fi

    if [ -e "$LAUNCHER_READY" ]; then
        /usr/bin/logger -t mira-plymouth-deferred-deactivate \
          "Launcher ready; deactivating Plymouth as fallback"

        /usr/bin/plymouth deactivate || true
        exit 0
    fi

    sleep 0.1
    COUNT=$((COUNT + 1))
done

/usr/bin/logger -p daemon.warning \
  -t mira-plymouth-deferred-deactivate \
  "Timeout waiting for MIRA background; deactivating Plymouth"

 /usr/bin/plymouth deactivate || true
exit 0
