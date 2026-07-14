# Apache-2.0 Open-Source Configuration Design

## Context

`uav-mission-intelligence-agent` is already hosted in a public GitHub repository, but it does not contain a root `LICENSE` file or declare a license in its Python package metadata. The existing maintenance documentation therefore correctly states that no general reuse permission has been granted.

The project owner selected the Apache License, Version 2.0 and requested the basic open-source configuration only. Community governance files such as `CONTRIBUTING.md`, `SECURITY.md`, a code of conduct, and issue templates are outside this change.

## Goals

- Grant users the permissions and protections defined by Apache-2.0.
- Make the license visible and machine-readable in the repository and Python distribution metadata.
- Ensure source and wheel distributions contain the license text.
- Replace the deferred-license statement in the project documentation with the adopted policy.
- Publish the verified change to the existing public GitHub repository.

## Non-goals

- Adding community governance or contribution-process files.
- Publishing the package to PyPI.
- Changing application behavior, dependencies, or APIs.
- Adding a `NOTICE` file when the project has no attribution notices that must be preserved.
- Adding license headers to every source file; the root license and package metadata define the repository-wide policy for this change.

## Approaches Considered

### 1. Local complete configuration, then push — selected

Add and validate all licensing changes locally, commit them together, and push the resulting commit. This keeps the repository, package metadata, and documentation consistent and provides a reviewable diff before publication.

### 2. Add only a root `LICENSE`

This would grant a clear repository-level license but leave Python distribution metadata incomplete and would not guarantee that built artifacts advertise and contain the license correctly.

### 3. Create the license through the GitHub web interface

GitHub can generate a license file, but a web-first commit would still require local edits for package metadata and documentation and could create an unnecessary synchronization conflict. The repository is already public, so no web-only configuration is required.

## Selected Changes

### Root license

Create `LICENSE` in the repository root using the unmodified official Apache License, Version 2.0 text. Do not add project-specific terms to the license text.

### Python package metadata

Update `[project]` in `pyproject.toml` with:

```toml
license = "Apache-2.0"
license-files = ["LICENSE"]
```

These fields follow PEP 639 and declare the SPDX license expression while explicitly including the license file in distribution archives. Because setuptools added support for these fields in version 77.0.3, update the build-system requirement from `setuptools>=68` to `setuptools>=77.0.3`.

Do not add a deprecated `License ::` classifier.

### README

Add a `License / 许可证` section stating that the project is licensed under Apache-2.0 and linking to the root `LICENSE` file. Add `LICENSE` to the repository structure listing so visitors can find it easily.

### Maintenance documentation

Replace the deferred decision in `docs/maintenance.md` with an adopted status. Record that the repository uses Apache-2.0, identify the root license and package metadata, and remove the obsolete pre-release checklist.

## Verification

1. Confirm the worktree contains only the intended files.
2. Run the existing offline unit-test suite.
3. Build both source and wheel distributions in a temporary output directory.
4. Inspect package metadata for `License-Expression: Apache-2.0` and a `License-File` entry.
5. Inspect both archives to confirm that the full `LICENSE` file is included.
6. Review the final diff and confirm there are no placeholder terms, contradictory license statements, or accidentally tracked credentials.

## GitHub Publication

The existing GitHub repository is already public. After verification, commit the implementation locally and push `main` to `origin`. GitHub should detect Apache-2.0 from the root `LICENSE` file automatically. No GitHub webpage action is required unless the push is rejected by branch protection or authentication; in that case, report the exact required user action rather than changing repository settings.

## Success Criteria

- GitHub contains a root `LICENSE` with the official Apache-2.0 text.
- README and maintenance documentation consistently identify Apache-2.0.
- `pyproject.toml` uses the SPDX expression and explicitly includes `LICENSE`.
- Tests pass and built distributions expose the correct license metadata and file.
- The verified implementation commit is present on `origin/main`.
