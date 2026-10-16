"""Tests for the presentation-independent installation planning service."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cli.application.install_plan import (
    InstallationRequest,
    build_installation_plan,
    load_catalogues,
    validate_installation_catalogues,
)


ROOT = Path(__file__).resolve().parents[1]


class InstallationPlanTests(unittest.TestCase):
    def setUp(self):
        self.catalogues = load_catalogues(ROOT)
        self.summary = validate_installation_catalogues(ROOT, self.catalogues)

    def test_real_catalogues_validate_through_application_boundary(self):
        self.assertEqual(self.summary.skill_count, 6)
        self.assertEqual(self.summary.mcp_count, 3)
        self.assertEqual(self.summary.client_count, 5)

    def test_builds_skill_plan_without_terminal_dependencies(self):
        with TemporaryDirectory() as temporary_home:
            request = InstallationRequest(
                root=ROOT,
                target_root=Path(temporary_home),
                scope='global',
                components=('skills',),
                clients=('kiro',),
                skills=('code-review', 'security-review'),
                mcp_servers=(),
            )

            installation = build_installation_plan(request, self.catalogues)
            changes = installation.deployment.planned_changes()

            self.assertTrue(changes)
            self.assertTrue(any(write.path.name == 'SKILL.md' for write in changes))
            self.assertTrue(all(Path(write.path).is_relative_to(Path(temporary_home)) for write in changes))

    def test_empty_request_produces_no_changes(self):
        with TemporaryDirectory() as temporary_home:
            request = InstallationRequest(
                root=ROOT,
                target_root=Path(temporary_home),
                scope='project',
                components=(),
                clients=(),
                skills=(),
                mcp_servers=(),
            )

            installation = build_installation_plan(request, self.catalogues)

            self.assertEqual(installation.deployment.planned_changes(), [])
            self.assertEqual(installation.servers, {})

    def test_invalid_scope_is_rejected_before_building(self):
        request = InstallationRequest(
            root=ROOT,
            target_root=ROOT,
            scope='workspace',
            components=(),
            clients=(),
            skills=(),
            mcp_servers=(),
        )

        with self.assertRaisesRegex(ValueError, 'Unsupported installation scope'):
            build_installation_plan(request, self.catalogues)


if __name__ == '__main__':
    unittest.main()
