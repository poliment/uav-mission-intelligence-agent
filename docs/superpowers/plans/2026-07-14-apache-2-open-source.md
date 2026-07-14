# Apache-2.0 Open-Source Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply Apache-2.0 consistently to the repository, Python distribution metadata, and user-facing documentation, verify the built artifacts, and publish the verified commits to `origin/main`.

**Architecture:** Treat licensing as a repository-level contract backed by a focused static test. The root `LICENSE` is the legal source, `pyproject.toml` supplies PEP 639 machine-readable metadata, and README plus maintenance documentation expose the decision to users and maintainers.

**Tech Stack:** Apache License 2.0, Python 3.10+, `unittest`, setuptools 77.0.3+, PEP 639, Git/GitHub

## Global Constraints

- Use the unmodified official Apache License, Version 2.0 text in root `LICENSE`.
- Use SPDX expression `Apache-2.0` and `license-files = ["LICENSE"]` in `[project]`.
- Require `setuptools>=77.0.3` for PEP 639 support.
- Do not add deprecated `License ::` classifiers.
- Do not add a `NOTICE` file or per-file license headers in this change.
- Do not add community governance files or publish the package to PyPI.
- Keep application behavior, runtime dependencies, and APIs unchanged.
- Push only after tests, artifact inspection, secret checks, and final diff review succeed.

---

## File Map

- Create `LICENSE`: authoritative, unmodified Apache License 2.0 legal text.
- Create `tests/test_license.py`: regression contract for the root license, PEP 639 metadata, and documentation statements.
- Modify `pyproject.toml`: declare Apache-2.0, package the license file, and raise the setuptools build floor.
- Modify `README.md`: add the public license statement and list `LICENSE` in the repository tree.
- Modify `tests/test_readme_assets.py`: include the new `License / 许可证` heading in the compact README structure contract.
- Modify `docs/maintenance.md`: record the completed licensing decision.

### Task 1: Add a failing repository license contract

**Files:**
- Create: `tests/test_license.py`
- Modify: `tests/test_readme_assets.py`

**Interfaces:**
- Consumes: repository files resolved from `Path(__file__).resolve().parents[1]`.
- Produces: a dependency-free `unittest` contract that fails until all Apache-2.0 files and declarations exist.

- [ ] **Step 1: Create the failing license test**

Create `tests/test_license.py` with:

```python
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LICENSE = REPO_ROOT / "LICENSE"
PYPROJECT = REPO_ROOT / "pyproject.toml"
README = REPO_ROOT / "README.md"
MAINTENANCE = REPO_ROOT / "docs" / "maintenance.md"


class LicenseTests(unittest.TestCase):
    def test_root_license_is_apache_2_0(self):
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
        self.assertIn("**Status:** Adopted.", maintenance)
        self.assertIn("Apache-2.0", maintenance)
        self.assertNotIn("Decision deferred", maintenance)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Update the README heading contract before the heading exists**

In `tests/test_readme_assets.py`, append `"License / 许可证"` after `"项目结构"` in the exact expected heading list:

```python
                "测试",
                "项目结构",
                "License / 许可证",
```

- [ ] **Step 3: Run the focused tests and confirm the red state**

Run:

```powershell
python -m unittest tests.test_license tests.test_readme_assets.ReadmeAssetsTests.test_readme_has_compact_console_first_structure -v
```

Expected: `test_root_license_is_apache_2_0` errors because root `LICENSE` does not exist; metadata and documentation assertions also fail.

### Task 2: Apply Apache-2.0 to the repository and package metadata

**Files:**
- Create: `LICENSE`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/maintenance.md`

**Interfaces:**
- Consumes: the failing contract from Task 1 and the official Apache text at `https://www.apache.org/licenses/LICENSE-2.0.txt`.
- Produces: repository-wide Apache-2.0 terms, PEP 639 metadata, and consistent user/maintainer documentation.

- [ ] **Step 1: Create the authoritative root license**

Copy the official text without modifications:

```powershell
Invoke-WebRequest -Uri "https://www.apache.org/licenses/LICENSE-2.0.txt" -OutFile "LICENSE"
```

Expected: `LICENSE` begins with `Apache License` and contains `Version 2.0, January 2004`.

- [ ] **Step 2: Add PEP 639 metadata and the supported build backend floor**

Update the opening `[project]` block in `pyproject.toml` to:

```toml
[project]
name = "uav-mission-intelligence-agent"
version = "0.1.0"
description = "Offline MVP for a UAV mission planning LLM/Agent project."
readme = "README.md"
requires-python = ">=3.10"
license = "Apache-2.0"
license-files = ["LICENSE"]
dependencies = []
```

Update the build requirement to:

```toml
[build-system]
requires = ["setuptools>=77.0.3"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 3: Add the README license section and tree entry**

Insert this line in the project tree after `README.md`:

```text
+-- LICENSE                  Apache License 2.0 全文
```

Append this section after the project tree code block:

```markdown
## License / 许可证

本项目采用 [Apache License 2.0](LICENSE) 开源许可证。你可以在许可证条款允许的范围内使用、修改和分发本项目。

This project is licensed under the [Apache License 2.0](LICENSE). You may use, modify, and distribute it in accordance with the license terms.
```

- [ ] **Step 4: Replace the deferred maintenance decision**

Replace the `## License` section of `docs/maintenance.md` with:

```markdown
## License

**Status:** Adopted.

The project is licensed under the Apache License, Version 2.0 (`Apache-2.0`). The authoritative terms are in the root [`LICENSE`](../LICENSE) file.

Python distribution metadata declares the SPDX expression and includes the license file through `pyproject.toml`. GitHub and package tooling can therefore identify the same repository-wide policy.
```

- [ ] **Step 5: Run the focused tests and confirm the green state**

Run:

```powershell
python -m unittest tests.test_license tests.test_readme_assets -v
```

Expected: all license and README tests pass.

- [ ] **Step 6: Commit the tested implementation**

```powershell
git add LICENSE pyproject.toml README.md docs/maintenance.md tests/test_license.py tests/test_readme_assets.py
git diff --cached --check
git commit -m "docs: license project under Apache 2.0"
```

Expected: one implementation commit containing exactly the six listed files.

### Task 3: Verify distribution artifacts and publish

**Files:**
- Inspect: `LICENSE`
- Inspect: `pyproject.toml`
- Inspect: generated temporary source and wheel archives under `tmp/license-dist/`
- Inspect: Git history and remote `origin/main`

**Interfaces:**
- Consumes: the implementation commit from Task 2.
- Produces: verified artifacts and synchronized `origin/main` with no generated build artifacts committed.

- [ ] **Step 1: Run the complete offline test suite**

```powershell
python -m unittest discover -s tests -v
```

Expected: all discovered tests pass; optional dependency tests may report skips, but no failures or errors.

- [ ] **Step 2: Build source and wheel distributions in an isolated environment**

```powershell
python -m pip install --target tmp/license-build-tool build
$env:PYTHONPATH = (Resolve-Path tmp/license-build-tool)
python -m build --sdist --wheel --outdir tmp/license-dist
```

Expected: one `.tar.gz` source distribution and one `.whl` wheel are created under `tmp/license-dist/` using setuptools 77.0.3 or newer.

- [ ] **Step 3: Inspect artifact metadata and included license files**

Run:

```powershell
python -c "import glob,tarfile,zipfile; s=glob.glob('tmp/license-dist/*.tar.gz')[0]; w=glob.glob('tmp/license-dist/*.whl')[0]; st=tarfile.open(s).getnames(); z=zipfile.ZipFile(w); wn=z.namelist(); m=[n for n in wn if n.endswith('.dist-info/METADATA')][0]; meta=z.read(m).decode(); assert 'License-Expression: Apache-2.0' in meta; assert 'License-File: LICENSE' in meta; assert any(n.endswith('/LICENSE') for n in st); assert any(n.endswith('.dist-info/licenses/LICENSE') for n in wn); print('Apache-2.0 metadata and license files verified')"
```

Expected: `Apache-2.0 metadata and license files verified`.

- [ ] **Step 4: Review the repository for accidental secrets and unintended files**

```powershell
git status --short
git diff HEAD~1 --check
git diff HEAD~1 --stat
git ls-files | rg -i '(^|/)(\.env($|\.)|.*secret.*|.*credential.*|id_rsa|id_ed25519|.*\.pem$|.*\.key$)'
```

Expected: the worktree is clean, the implementation diff contains only the intended six files, and the tracked secret-like filename scan returns no matches.

- [ ] **Step 5: Push both local commits to the existing public repository**

```powershell
git push origin main
```

Expected: Git reports `main -> main` and no GitHub webpage intervention is required.

- [ ] **Step 6: Verify the remote branch contains the implementation**

```powershell
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
```

Expected: both commit hashes are identical. GitHub should identify the repository license as Apache-2.0 from root `LICENSE`.
