#!/usr/bin/env python3
"""Questions RS scraper — Rajya Sabha only.

Writes to docs/questions-rs/. Deployed to its own Cloudflare Pages
project in the 4-way split. See README §"Repo layout" for the full
picture.

This wrapper sets the env vars that drive _questions_core.py's per-
house gating, then delegates to it. The bulk of the logic lives in
the core; this file only owns the RS-specific configuration.

Note on RS_SESSIONS default: the core defaults to `recent-2` (walk
the two most recent sessions per cron firing). For the initial
backfill into the new repo, dispatch with `RS_SESSIONS=all` once
via workflow_dispatch to walk every session the API exposes.
"""
import os
import runpy
from pathlib import Path

os.environ.setdefault("BUILDER_DOCS_SUBDIR",  "questions-rs")
os.environ.setdefault("BUILDER_CORPUS_NAME",  "questions-rs")
os.environ.setdefault("BUILDER_HOUSE_FILTER", "rs")

runpy.run_path(str(Path(__file__).resolve().parent / "_questions_core.py"), run_name="__main__")
