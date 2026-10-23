#!/bin/sh
# PC2 sandbox interface: memory MB, CPU seconds, program.
exec /usr/bin/sudo -n /opt/lcpc/bin/sandbox-broker.py run "$@"
