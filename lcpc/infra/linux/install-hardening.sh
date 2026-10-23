#!/bin/sh
set -eu
[ "$(id -u)" = 0 ]
install -o root -g root -m 0755 /tmp/lcpc-stage/sandbox-broker.py /opt/lcpc/bin/sandbox-broker.py
install -o root -g root -m 0755 /tmp/lcpc-stage/compile17 /opt/lcpc/bin/compile17
install -o root -g root -m 0755 /tmp/lcpc-stage/compile20 /opt/lcpc/bin/compile20
install -o root -g root -m 0755 /tmp/lcpc-stage/compilepython /opt/lcpc/bin/compilepython
install -o root -g root -m 0755 /tmp/lcpc-stage/runpython /opt/lcpc/bin/runpython
install -d -o root -g root -m 0755 /opt/lcpc/scripts
install -o root -g root -m 0755 /tmp/lcpc-stage/pc2sandbox.sh /opt/lcpc/scripts/pc2sandbox.sh
install -o root -g root -m 0755 /tmp/lcpc-stage/pc2syscheck.sh /opt/lcpc/scripts/pc2syscheck.sh
printf 'pc2judge ALL=(root) NOPASSWD: /opt/lcpc/bin/sandbox-broker.py *\n' > /etc/sudoers.d/lcpc-sandbox
chmod 0440 /etc/sudoers.d/lcpc-sandbox
visudo -cf /etc/sudoers.d/lcpc-sandbox
# Bound the coordinator itself; sandbox job units receive their own stricter limits.
mkdir -p /etc/systemd/system/pc2judge.service.d

install -o root -g root -m 0755 /tmp/lcpc-stage/healthcheck.sh /opt/lcpc/bin/healthcheck.sh
install -o root -g root -m 0644 /tmp/lcpc-stage/pc2judge.service /etc/systemd/system/pc2judge.service
systemctl daemon-reload
