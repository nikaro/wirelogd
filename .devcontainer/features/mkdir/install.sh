#!/usr/bin/env sh

set -o errexit # Exit on error
set -o nounset # Exit on uninitialized variable

# exit if no directories are specified
[ -z "${DIRECTORIES:-}" ] && exit 0

# ensure directories are separated by spaces
DIRECTORIES=$(printf '%s' "$DIRECTORIES" | tr ',' ' ')

# create directories
mkdir -p $DIRECTORIES

# change permissions of directories
[ -z "${PERMISSIONS:-}" ] || chmod $PERMISSIONS $DIRECTORIES

# change ownership of directories
[ -z "${OWNER:-}" ] || chown $OWNER $DIRECTORIES
