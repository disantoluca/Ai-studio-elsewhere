#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression tests for the project-lifecycle null-state repair (2026-09-30).

load_project() -> Optional[Project] already declared None as a legitimate
outcome (missing Postgres row + missing local fallback file, or a corrupt
file). Eight call sites in ai_studio_elsewhere.py dereferenced the result
(.scenes, .title_en, ...) without checking for None first, producing:

    AttributeError: 'NoneType' object has no attribute 'scenes'

whenever a selected project's backing data was actually unavailable (most
likely: Railway's ephemeral container filesystem wiped locally-stored
project JSON files across a redeploy, with no persistent Volume or
DATABASE_URL configured).

ai_studio_elsewhere.py is a monolithic top-level Streamlit script, not
structured as importable functions behind `if __name__ == "__main__"`.
It can be imported directly in "bare mode" (Streamlit just warns about a
missing ScriptRunContext rather than raising), which lets us exercise the
real load_project()/_project_unavailable_warning() functions end-to-end.
But the 8 call sites themselves are inline script statements, not
functions we can invoke individually — so their protection is verified
structurally (source-pattern matching) rather than by executing each tab.
Both approaches are combined here for real coverage of the underlying
contract plus a hard guarantee that every call site actually uses it.
"""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_FILE = REPO_ROOT / "ai_studio_elsewhere.py"


def _run_fresh(script: str, env_extra: dict) -> subprocess.CompletedProcess:
    import os
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


class TestLoadProjectNoneContract(unittest.TestCase):
    """Real, end-to-end behavior of load_project() when data is absent."""

    def test_load_project_returns_none_with_no_backing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = _run_fresh(
                "import ai_studio_elsewhere as app\n"
                "result = app.load_project('a-project-id-that-was-never-created')\n"
                "print('RESULT_IS_NONE=' + str(result is None))\n",
                {"DATA_DIR": tmp, "DATABASE_URL": ""},
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("RESULT_IS_NONE=True", proc.stdout)

    def test_load_project_finds_a_real_saved_project(self):
        """Sanity check: the None case above is specifically about missing
        data, not a broken function — a genuinely saved project must still
        load correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            proc = _run_fresh(
                "import ai_studio_elsewhere as app\n"
                "p = app.Project(project_id='p1', title_en='Test', title_zh='',\n"
                "                 director='', logline='', created_at='', last_updated='',\n"
                "                 script_path=None, scenes=[], concepts={})\n"
                "app.save_project(p)\n"
                "result = app.load_project('p1')\n"
                "print('RESULT_IS_NONE=' + str(result is None))\n"
                "print('TITLE=' + (result.title_en if result else ''))\n",
                {"DATA_DIR": tmp, "DATABASE_URL": ""},
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("RESULT_IS_NONE=False", proc.stdout)
            self.assertIn("TITLE=Test", proc.stdout)


class TestProjectUnavailableWarning(unittest.TestCase):
    """The warning must state that data is unavailable without asserting
    a specific, unknowable cause (approved wording, 2026-09-30)."""

    def test_warning_message_is_diagnostically_honest(self):
        proc = _run_fresh(
            "import ai_studio_elsewhere as app\n"
            "captured = {}\n"
            "app.st.warning = lambda msg: captured.setdefault('msg', msg)\n"
            "app._project_unavailable_warning()\n"
            "print('MSG=' + captured['msg'])\n",
            {},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        msg_line = next(l for l in proc.stdout.splitlines() if l.startswith("MSG="))
        message = msg_line[len("MSG="):]
        self.assertIn("could not be loaded", message)
        self.assertIn("persistent storage configuration", message)
        # Must not assert a specific cause as fact.
        self.assertNotIn("was reset by", message)
        self.assertNotIn("has been deleted", message)


class TestAllCallSitesProtected(unittest.TestCase):
    """Structural guarantee: every `project = load_project(selected_project)`
    in the app must be immediately followed by a None check. Catches any
    future call site added without the guard, or a guard accidentally
    removed from an existing one."""

    TARGET = "project = load_project(selected_project)"
    EXPECTED_SITE_COUNT = 8

    def test_every_load_project_call_site_checks_for_none(self):
        text = APP_FILE.read_text(encoding="utf-8")
        lines = text.splitlines()

        site_indices = [i for i, l in enumerate(lines) if l.strip() == self.TARGET]
        self.assertEqual(
            len(site_indices), self.EXPECTED_SITE_COUNT,
            f"Expected {self.EXPECTED_SITE_COUNT} load_project(selected_project) call "
            f"sites, found {len(site_indices)}. If you added or removed one "
            f"intentionally, update EXPECTED_SITE_COUNT and confirm the new/remaining "
            f"site(s) still check for None."
        )

        for idx in site_indices:
            # Find the next non-blank line after the call site.
            j = idx + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            self.assertLess(j, len(lines), f"No line found after site at {idx + 1}")
            self.assertEqual(
                lines[j].strip(), "if project is None:",
                f"Call site at ai_studio_elsewhere.py:{idx + 1} is not immediately "
                f"followed by a None check (found: {lines[j].strip()!r})."
            )

    def test_helper_is_used_by_every_guarded_site(self):
        text = APP_FILE.read_text(encoding="utf-8")
        # def + N call sites
        self.assertEqual(
            text.count("_project_unavailable_warning()"),
            self.EXPECTED_SITE_COUNT + 1,
        )


if __name__ == "__main__":
    unittest.main()
