#!/bin/sh
# Compatibility entry point; implementation: mira-core/media/audio/rnse-bluetooth-autoconnect.sh
_mira_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
exec /bin/bash "$_mira_dir/../mira-core/media/audio/rnse-bluetooth-autoconnect.sh" "$@"
