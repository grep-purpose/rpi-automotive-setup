#!/bin/sh

# IMPORTANT:
# Do not intercept "deactivate".
# LightDM must be able to release the graphics device so labwc can start.

# Defer only the final retained-splash quit until the launcher is ready.
if [ "$#" -eq 2 ] &&
   [ "$1" = "quit" ] &&
   [ "$2" = "--retain-splash" ]; then

    /usr/bin/logger -t mira-plymouth-wrapper \
      "Deferring retained-splash quit until launcher is ready"

    /usr/bin/nohup \
      /usr/local/sbin/mira-plymouth-deferred-quit \
      </dev/null >/tmp/mira-plymouth-deferred-quit.log 2>&1 &

    exit 0
fi

# All other commands, including deactivate, go to the original program.
exec /usr/bin/plymouth "$@"
