# Changelog

All notable changes to this framework are recorded here. `readme.md` always
describes the **current** release and nothing else; this file is where
release-to-release history lives, so the README never accumulates a sediment of
"as of version X" qualifiers.

Each README section carries the release and date its content last changed
(`<sub>v1.0.0 &middot; 2026-08-10</sub>`). Together the two answer different
questions: the stamp tells a reader arriving at a later version *which sections
moved*, and an entry here tells them *what changed and why*. A changelog entry
alone does not tell you where to look.

Versions follow [Semantic Versioning](https://semver.org/) as applied to a test
framework:

- **Major** - a change that breaks an existing invocation or configuration.
- **Minor** - new coverage, new capability, or a new quality gate.
- **Patch** - fixes and documentation corrections that change no behaviour.

Dates are **UTC**, matching git commit dates and CI runners, so a stamp written
in the evening in one timezone still agrees with the commit that carries it.

---

## v1.0.0 - 2026-08-10

First release under version tracking. The framework predates this file;
commit-level history before this point is in git. This entry records the state
as shipped, and the changes that landed with it.

### Added

- **`CHANGELOG.md` and per-section documentation stamps** in `readme.md`.

### Changed

- **Project Structure** corrected against the actual repository. Six tracked
  files were missing from the documented tree - `conftest.py`, `pytest.ini`,
  `.pylintrc`, `Makefile`, `requirements.txt` and `readme.md` itself - while
  `allure-results/` was listed among them despite being generated and ignored.
  The tree now separates what is committed from what a run produces.

### Known issues

- **`test_results/report.html` and `test_results/results.xml` are still
  tracked.** They were committed before `test_results/` was added to
  `.gitignore`, and an ignore rule does not untrack what git already knows
  about. Because `make clean` removes the directory, a local `make test` leaves
  two deletions in `git status` unrelated to whatever is being worked on.
  `git rm --cached` on both resolves it; they are build output, and the ignore
  rule already records that they were never meant to be committed.

### Notes

- **Concurrency is deliberately inverted here** relative to the other pipelines
  in this portfolio. Runs are serialized account-wide under a branch-agnostic
  group with `cancel-in-progress: false`, because the scarce resource is an
  external shared API quota rather than runner minutes: a per-branch group would
  let two branches race the same rate limit, and cancelling an in-flight run
  would spend quota on a result nobody reads. The scarce resource dictates the
  policy.
- **The suite runs serially by design**, not for lack of `pytest-xdist`. The
  provider limits requests per IP, so parallel execution would produce a cascade
  of failures that say nothing about the application under test. That decision
  is also what makes the session-wide request-pacing clock correct without
  cross-process coordination.
- `Makefile` casing is load-bearing: GNU make auto-discovers only `GNUmakefile`,
  `makefile`, or `Makefile`. The original `MakeFIle` resolved on a
  case-insensitive local filesystem and failed on `ubuntu-latest`.
