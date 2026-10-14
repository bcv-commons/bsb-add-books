#!/usr/bin/env python3
"""Moved: the learning tool is now general, `python3 scripts/concord.py kvg/kvg_BSB <command> …`
(docs/proposals/language-toolkit/). This wrapper keeps the old calls working: the `kvg` command searches
the Kuni text, as before."""
import os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.exit(subprocess.call([sys.executable, os.path.join(ROOT, "scripts", "concord.py"), "kvg/kvg_BSB", *sys.argv[1:]]))
