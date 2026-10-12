#!/bin/sh

# Keep the MIRA animation running until the launcher is ready.
if [ "$#" -eq 1 ] &&
   [ "$1" = "deactivate" ] &&
   [ ! -e /run/user/1000/mira-launcher-ready ]; then

    /usr/bin/logger -t mira-plymouth-wrapper \
      "Keeping Plymouth active until MIRA launcher is ready"

    exit 0
fi

# Defer the final retained-splash handoff until the launcher is ready.
if [ "$#" -eq 2 ] &&
   [ "$1" = "quit" ] &&
   [ "$2" = "--retain-splash" ]; then

    /usr/bin/logger -t mira-plymouth-wrapper \
      "Deferring Plymouth quit until launcher is ready"

    /usr/bin/nohup \
      /usr/local/sbin/mira-plymouth-deferred-quit \
      </dev/null >/tmp/mira-plymouth-deferred-quit.log 2>&1 &

    exit 0
fi

exec /usr/bin/plymouth "$@"
