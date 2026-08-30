#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from audit_skill_hygiene import check_active_entrypoint_commands, check_resolver_isolation  # noqa: E402


class ThinSkillHygieneTests(unittest.TestCase):
    def test_active_router_may_call_only_allowlisted_maintenance_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SKILL.md").write_text(
                "python3 scripts/resolve_website_content_ops_root.py --json\n"
                "python3 scripts/audit_skill_hygiene.py\n",
                encoding="utf-8",
            )
            self.assertEqual(check_active_entrypoint_commands(root), [])

    def test_active_router_rejects_a_legacy_mutation_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SKILL.md").write_text(
                "python3 scripts/check_pre_mutation_gate.py --execute\n",
                encoding="utf-8",
            )
            issues = check_active_entrypoint_commands(root)
            self.assertEqual(len(issues), 1)
            self.assertIn("non-authoritative local script", issues[0])

    def test_resolver_rejects_import_of_a_local_legacy_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "legacy_executor.py").write_text("VALUE = 1\n", encoding="utf-8")
            (scripts / "resolve_website_content_ops_root.py").write_text(
                "import legacy_executor\n",
                encoding="utf-8",
            )
            issues = check_resolver_isolation(root)
            self.assertEqual(len(issues), 1)
            self.assertIn("legacy_executor", issues[0])

    def test_current_resolver_is_isolated_from_legacy_helpers(self) -> None:
        root = SCRIPTS_DIR.parent
        self.assertEqual(check_resolver_isolation(root), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
