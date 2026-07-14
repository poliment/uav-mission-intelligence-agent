import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LICENSE = REPO_ROOT / "LICENSE"
PYPROJECT = REPO_ROOT / "pyproject.toml"
README = REPO_ROOT / "README.md"
MAINTENANCE = REPO_ROOT / "docs" / "maintenance.md"


class LicenseTests(unittest.TestCase):
    def test_root_license_is_apache_2_0(self):
        self.assertTrue(LICENSE.exists(), "root LICENSE file is missing")
        license_text = LICENSE.read_text(encoding="utf-8")

        self.assertIn("Apache License", license_text)
        self.assertIn("Version 2.0, January 2004", license_text)
        self.assertIn("http://www.apache.org/licenses/", license_text)
        self.assertIn("END OF TERMS AND CONDITIONS", license_text)

    def test_package_metadata_declares_and_packages_license(self):
        pyproject = PYPROJECT.read_text(encoding="utf-8")

        self.assertIn('license = "Apache-2.0"', pyproject)
        self.assertIn('license-files = ["LICENSE"]', pyproject)
        self.assertIn('requires = ["setuptools>=77.0.3"]', pyproject)
        self.assertNotIn("License ::", pyproject)

    def test_documentation_states_the_adopted_license(self):
        readme = README.read_text(encoding="utf-8")
        maintenance = MAINTENANCE.read_text(encoding="utf-8")

        self.assertIn("## License / 许可证", readme)
        self.assertIn("[Apache License 2.0](LICENSE)", readme)
        self.assertNotIn("维护期未决事项", readme)
        self.assertIn("**Status:** Adopted.", maintenance)
        self.assertIn("Apache-2.0", maintenance)
        self.assertNotIn("Decision deferred", maintenance)


if __name__ == "__main__":
    unittest.main()
