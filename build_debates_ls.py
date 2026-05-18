#!/usr/bin/env python3
"""Debates LS scraper — Lok Sabha only.

Writes to docs/debates-ls/. Deployed to its own Cloudflare Pages project
in the 4-way split. See README §"Repo layout" for the full picture.

This wrapper sets the env vars that drive _debates_core.py's per-house
gating, then delegates to it. The bulk of the logic (walk, extract,
derive, manifest, audit, search bundle/index, write_meta) lives in the
core; this file only owns the LS-specific configuration.
"""
import os
import runpy
from pathlib import Path

os.environ.setdefault("BUILDER_DOCS_SUBDIR",  "debates-ls")
os.environ.setdefault("BUILDER_CORPUS_NAME",  "debates-ls")
os.environ.setdefault("BUILDER_HOUSE_FILTER", "ls")

runpy.run_path(str(Path(__file__).resolve().parent / "_debates_core.py"), run_name="__main__")
