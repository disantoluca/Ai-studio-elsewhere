#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression test for the root/agents/ module-shadowing defect discovered
2026-09-30 while diagnosing a production Runway failure.

Root cause: cinematic_localization_ui.py and cinematic_evaluation_ui.py
each inserted the agents/ directory at sys.path[0] as a side effect of
being imported, purely so they could do bare `from cinematic_localization_
agent import ...` / `from localization_evaluator import ...`. Because
agents/runway_video_agent.py and agents/google_places_agent.py happen to
share filenames with real modules at the repo root, any later bare
`import runway_video_agent` (e.g. from runway_video_ui.py) resolved to the
wrong, older file — which lacks get_generation_history() — instead of the
intended root module. This reproduced in production as:

    'RunwayVideoAgent' object has no attribute 'get_generation_history'

The fix: stop mutating sys.path; use package-qualified imports
(`agents.cinematic_localization_agent`, `agents.localization_evaluator`)
instead, which Python 3 resolves correctly as implicit namespace packages
with no __init__.py and no sys.path changes required.

This test pins the actual failure condition — importing the cinematic UI
modules BEFORE runway_video_agent is ever imported, exactly as
ai_studio_elsewhere.py does at module load — and asserts resolution still
lands on the intended root module in each case. It deliberately runs each
scenario in a fresh subprocess: sys.modules / sys.path caching means the
bug (or its absence) is only observable on a first-ever import in a clean
interpreter, and this suite otherwise shares a process with other test
files that may already have imported these modules.
"""

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_fresh(script: str) -> subprocess.CompletedProcess:
    """Run `script` in a brand-new Python process, cwd'd at the repo root,
    so sys.modules / sys.path start empty exactly like a real app boot."""
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestAgentsImportBoundary(unittest.TestCase):

    def test_cinematic_uis_do_not_add_agents_to_syspath(self):
        proc = _run_fresh(
            "import sys\n"
            "import cinematic_localization_ui\n"
            "import cinematic_evaluation_ui\n"
            "shadowed = any(p.rstrip('/').endswith('agents') for p in sys.path)\n"
            "print('AGENTS_ON_PATH=' + str(shadowed))\n"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("AGENTS_ON_PATH=False", proc.stdout)

    def test_runway_video_agent_resolves_to_root_after_cinematic_ui_imports(self):
        """The actual failure condition: import the cinematic UI modules
        first (as ai_studio_elsewhere.py does at module load, before
        Runway is ever touched), then import runway_video_agent bare, the
        same way runway_video_ui.py does."""
        proc = _run_fresh(
            "import cinematic_localization_ui\n"
            "import cinematic_evaluation_ui\n"
            "import runway_video_agent\n"
            "print('RESOLVED=' + runway_video_agent.__file__)\n"
            "print('HAS_METHOD=' + str(hasattr(runway_video_agent.RunwayVideoAgent, 'get_generation_history')))\n"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(str(REPO_ROOT / "runway_video_agent.py"), proc.stdout)
        self.assertNotIn(str(REPO_ROOT / "agents" / "runway_video_agent.py"), proc.stdout)
        self.assertIn("HAS_METHOD=True", proc.stdout)

    def test_google_places_agent_resolves_to_root_after_cinematic_ui_imports(self):
        """Same shadowing hazard existed for a second duplicate filename —
        silently, since both versions define a class of the same name and
        neither import raised an error."""
        proc = _run_fresh(
            "import cinematic_localization_ui\n"
            "import cinematic_evaluation_ui\n"
            "import google_places_agent\n"
            "print('RESOLVED=' + google_places_agent.__file__)\n"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(str(REPO_ROOT / "google_places_agent.py"), proc.stdout)
        self.assertNotIn(str(REPO_ROOT / "agents" / "google_places_agent.py"), proc.stdout)

    def test_qualified_agents_imports_still_work(self):
        """The repair must not break what the sys.path mutation used to
        provide — agents.cinematic_localization_agent and
        agents.localization_evaluator must still import cleanly via
        Python's implicit namespace packages, with no sys.path change."""
        proc = _run_fresh(
            "from agents.cinematic_localization_agent import LocalizationOrchestrator\n"
            "from agents.localization_evaluator import EvalCase\n"
            "print('OK')\n"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)

    def test_cinematic_ui_modules_still_report_available(self):
        proc = _run_fresh(
            "import cinematic_localization_ui as a\n"
            "import cinematic_evaluation_ui as b\n"
            "print('AGENT_AVAILABLE=' + str(a.AGENT_AVAILABLE))\n"
            "print('EVAL_AVAILABLE=' + str(b.EVAL_AVAILABLE))\n"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("AGENT_AVAILABLE=True", proc.stdout)
        self.assertIn("EVAL_AVAILABLE=True", proc.stdout)


if __name__ == "__main__":
    unittest.main()
