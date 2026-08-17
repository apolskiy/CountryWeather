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

## v1.3.0 - 2026-08-16

### Added

- **Every test now carries an assigned, stable identifier.** Nine tests are
  marked `CWA_10001` through `CWA_10009` via `@pytest.mark.test_id(...)`; the
  next free number is `CWA_10010`, and numbers are never reused.

  The identifier exists because a test's name is not a stable identity. Any
  store keyed on the name forks a test's history the moment it is renamed -
  silently, because both halves still look like valid tests, and the only
  symptom is one long record quietly becoming two short ones. The suite's names
  should stay free to improve; this is what makes that free.

  `conftest.py` republishes the marker at collection time in
  `_publish_test_ids`, as both an Allure label and a JUnit `<property>`, so the
  marker is authored once and reaches two reporters that do not talk to each
  other. Collection time rather than a fixture, deliberately: the label is
  attached before any reporter begins building a result, so it cannot be lost to
  fixture ordering. Verified end to end - a `--env=weather` run produced ten
  Allure results and ten JUnit properties, all carrying the ID, and
  [PortfolioTestInsights](https://github.com/apolskiy/PortfolioTestInsights)
  read it back from both formats.

- **`test_id` registered as a marker** in `pytest.ini` and in
  `pytest_configure`. Required rather than cosmetic: this suite runs under
  `--strict-markers`, so an unregistered marker is an error, not a warning.

### Notes

- No test was renamed and no behaviour changed. The diff is decorator
  insertions plus the conftest hook.
- The identifier is additive for history: the collector keys on
  `COALESCE(test_id, test_uid)`, so results recorded before these IDs existed -
  including artifacts now expired - still stitch to results recorded after.

---

## v1.2.0 - 2026-08-13

### Added

- **Static analysis is now a gate rather than an aspiration.** `readme.md` and
  `.claude/rules/framework-rules.md` both stated that code must pass Pylint, and
  a `.pylintrc` sat in the repository root, but nothing ever ran it: no CI step,
  no Make target. The suite scored **9.45/10** when finally measured.

  CI gains a `lint` job running `make lint` (`pylint --fail-under=10` over every
  tracked `.py` file), and the `test` job now declares `needs: lint`. The
  ordering is this project's quota argument applied to itself - the linter needs
  no API key and spends nothing, so failing there costs seconds, while running
  the suite first would spend capped monthly requests to learn something static
  analysis already knew. `--fail-under=10` rather than a softer floor, matching
  PublicAP: a score allowed to drift is not a gate, because it never fails a
  build, it just gets quietly worse.

  The file list comes from `git ls-files '*.py'` rather than being written into
  the recipe, for the same reason the trigger is a `paths-ignore` denylist - a
  hand-maintained list silently stops covering a directory the day someone
  forgets to add it. The Makefile owns the invocation, so `make lint` locally and
  in CI are the same command, as with `make test`.

- **`pylint==4.0.6`** pinned in `requirements.txt`, matching the version PublicAP
  gates on. Kept in the single requirements file rather than split into a dev
  set: the linter must import every third-party name the suite imports in order
  to resolve them, so the two dependency sets are the same set plus one entry.

### Fixed

- **`.pylintrc` was never in effect.** Its first line was the stray text
  `Ini, TOML` - a language label pasted in when the file was generated - which
  left the file with no section header before its first key. Pylint reported
  `F0011: error while parsing the configuration` and fell back to built-in
  defaults for every run. Confirmed rather than assumed: a probe copy carrying
  the same stray line and `max-line-length=40` failed to flag a 50-character
  line. Nothing downstream had noticed because the only setting that could have
  changed a result, `max-line-length=100`, happens to equal Pylint's own
  default. The stray line is removed and the file now parses.

- **`ignore=tests/conftest.py` removed.** It named a path that does not exist -
  `conftest.py` lives at the repository root - so it excluded nothing even had
  the file parsed. The root `conftest.py` is linted, and passes.

- **Nineteen findings cleared to reach 10.00/10.** Seventeen lines exceeded the
  declared 100-character limit (worst: 117 in `tests/test_weather.py`), wrapped
  without changing behaviour. `conftest.py` opened `config/environments.yaml`
  with no explicit encoding, which resolves to the platform default and would
  misread a non-ASCII value on a Windows console - now pinned to UTF-8. The two
  unused arguments in `pytest_sessionfinish` carry a scoped disable and a
  comment, since pytest matches hook parameters by name and neither can be
  renamed or dropped.

- **`max-attributes` raised to 12,** with the reason recorded in `.pylintrc`.
  `ApiClient` holds one attribute per configuration key from
  `config/environments.yaml` (11) and `CountrySchema` mirrors the fields of a
  REST Countries v5 object (8). Both counts are dictated by an external contract
  rather than by a class doing too much, so the limit is raised deliberately
  rather than evaded by bagging unrelated values into a dict.

- **`.claude/rules/code-style.md` held the wrong content.** It was a
  byte-for-byte copy of `testing-standards.md` - same title, same three sections
  - so the repository declared three rules files and shipped two, with no code
  style rules at all. It now documents the conventions the code actually
  follows: naming, type annotations, docstring formatting, imports, layout, data
  and failure handling, and comments. Every rule was derived by reading the
  existing modules, and the two places where the code contradicts itself are
  named as such - the validators still import `Dict`/`List` from `typing` where
  the rest of the suite uses built-in generics.

---

## v1.1.0 - 2026-08-10

### Changed

- **CI no longer runs on commits that cannot change the result.** The workflow
  triggered on every push and pull request to any branch, so a documentation-only
  commit ran the full suite against the live REST Countries API and spent
  capped monthly quota re-confirming a result that could not have moved. Proven
  rather than assumed: publishing v1.0.0 - a README and a changelog, no source -
  fired run `31351644391` and did exactly that.

  This contradicted the project's own reasoning. The quota being the scarce
  resource is why runs are serialized account-wide, why `cancel-in-progress` is
  `false`, and why `pytest-xdist` was rejected; spending it on Markdown belongs
  to none of that. Both sibling repositories already handled it - PublicAP
  path-filters its emulator suite, and the portfolio site skips its dispatch for
  non-`.html/.css/.js` commits.

  The trigger now carries `paths-ignore` for `**.md`, `LICENSE`, `.gitignore`
  and `.idea/**`. A denylist rather than an allowlist, deliberately: an
  allowlist must be extended whenever a directory is added, and forgetting is
  silent - new code that never runs in CI while the badge stays green. A
  denylist fails the other way, where the worst case is one unnecessary run that
  costs quota once and is visible. `workflow_dispatch` still forces a run.

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
