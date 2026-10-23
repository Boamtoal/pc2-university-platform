#!/usr/bin/env python3
"""Convenient entry point for the separate isolated infrastructure test contest."""
from pathlib import Path
import sys,os
root=Path(__file__).resolve().parents[1]
env={**os.environ,'LCPC_STATE_DIR':str(root/'.local/instances/linux-trial')}
os.execve(sys.executable,[sys.executable,str(root/'lcpc/pc2ctl.py'),*sys.argv[1:]],env)
