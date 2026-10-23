#!/bin/sh
# PC2 9.10 invokes this hook before enabling its internal sandbox interface.
# Our cgroup-v2 broker must pass a real compile/run isolation probe.
exec sudo -n /opt/lcpc/bin/sandbox-broker.py check
