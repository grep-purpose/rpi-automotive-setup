#!/bin/sh
# Compatibility entry point; implementation: platform/launcher/launch_hudiy.sh
_mira_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
exec /bin/bash "$_mira_dir/../platform/launcher/launch_hudiy.sh" "$@"
