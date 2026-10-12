#!/bin/sh

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
