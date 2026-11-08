import unittest
import urllib.error
from unittest.mock import patch

import unpublish_npm as workflow


class UnpublishNpmTests(unittest.TestCase):
    version = "3000.12.1"
    targets = (
        version,
        f"{version}-darwin-arm64",
        f"{version}-darwin-x64",
        f"{version}-linux-arm64",
        f"{version}-linux-x64",
        f"{version}-win32-arm64",
        f"{version}-win32-x64",
    )

    def test_exact_launcher_and_platform_versions(self):
        self.assertEqual(workflow.planned_versions(self.version), self.targets)
        for unsafe in ("latest", "*", ">=3000.12.1", "3000.12.1-linux-x64", "3000.12.1/../2", "--force"):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                workflow.planned_versions(unsafe)

    def test_preflight_refuses_current_stable(self):
        with patch.object(workflow, "get_json", return_value={"version": self.version}):
            with self.assertRaisesRegex(ValueError, "current Stable"):
                workflow.preflight(self.version, self.targets)

    def test_preflight_requires_a_yank_marker(self):
        with patch.object(workflow, "get_json", side_effect=[{"version": "3000.12.2"}, {}]):
            with self.assertRaisesRegex(ValueError, "must be yanked"):
                workflow.preflight(self.version, self.targets)

    def test_preflight_refuses_a_tagged_variant(self):
        with patch.object(workflow, "get_json", side_effect=[
            {"version": "3000.12.2"},
            {"yanked": True},
            {"dist-tags": {"linux-x64": f"{self.version}-linux-x64"}},
        ]):
            with self.assertRaisesRegex(ValueError, "linux-x64"):
                workflow.preflight(self.version, self.targets)

    def test_preview_never_calls_npm(self):
        with patch.object(workflow, "preflight", return_value=list(self.targets)), patch("subprocess.run") as npm:
            workflow.unpublish(self.version, execute=False)
        npm.assert_not_called()

    def test_execute_only_removes_present_versions_and_checks_every_tarball(self):
        present = [self.version, f"{self.version}-linux-x64"]
        with (
            patch.object(workflow, "preflight", return_value=present),
            patch.dict("os.environ", {"NODE_AUTH_TOKEN": "test"}),
            patch("subprocess.run") as npm,
            patch.object(workflow, "verify") as verify,
        ):
            workflow.unpublish(self.version, execute=True)
        self.assertEqual([call.args[0][:3] for call in npm.call_args_list], [
            ["npm", "unpublish", f"devin@{target}"] for target in present
        ])
        self.assertTrue(all("--force=false" in call.args[0] for call in npm.call_args_list))
        verify.assert_called_once_with(self.targets)

    def test_verification_fails_if_tarball_is_still_reachable(self):
        with (
            patch.object(workflow, "get_json", return_value={"versions": {}}),
            patch.object(workflow, "tarball_gone", return_value=False),
            patch("time.sleep"),
        ):
            with self.assertRaisesRegex(ValueError, "Still publicly reachable"):
                workflow.verify(self.targets)

    def test_tarball_auth_failure_does_not_count_as_removal(self):
        with patch.object(workflow, "request", side_effect=urllib.error.HTTPError("", 403, "", None, None)):
            with self.assertRaises(urllib.error.HTTPError):
                workflow.tarball_gone(self.version)
