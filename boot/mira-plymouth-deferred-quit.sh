#!/bin/sh
set -u

MARKER="/run/user/1000/mira-launcher-ready"
COUNT=0

while [ "$COUNT" -lt 450 ]; do
    if [ -e "$MARKER" ]; then
        /usr/bin/logger -t mira-plymouth-deferred-quit \
          "Launcher ready; closing Plymouth"

        /usr/bin/plymouth quit --retain-splash
        exit $?
    fi

    sleep 0.1
    COUNT=$((COUNT + 1))
done

/usr/bin/logger -p daemon.warning \
  -t mira-plymouth-deferred-quit \
  "Timeout: launcher marker missing; closing Plymouth"

 /usr/bin/plymouth quit --retain-splash || true
exit 0
