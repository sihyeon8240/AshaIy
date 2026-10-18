# Repository tests

Install the pinned tools with `python3 -m pip install -r .github/requirements-ci.txt`
or use the rebuilt development image. Run the suite with `ashaiy test`.
For a focused run, use discovery so shared helpers remain importable:

```bash
python3 -m unittest discover -s tests -p 'test_build_commands.py' -v
```

Test observable repository contracts: canonical manifests and generated assembly,
build selection and failure propagation, Lean proof correspondence, source
preservation, and safe image/release/snapshot publication. Keep focused parser
regressions where a failure could silently corrupt these operations. Avoid tests
that only repeat argparse help, mock a one-line dispatcher, or freeze template
structure, stylesheet names, and editor preferences. Check actual generated
output and rendered behavior instead. Keep unit and integration checks when they
exercise different boundaries. Script syntax and workflow semantics belong to
the existing source checks and actionlint.

`test_properties.py` uses Hypothesis to exercise TeX parsing, source positions,
semantic versions, and manifest normalization. Minimized failures live under
`.cache/hypothesis/`. Keep fixed examples for known regressions.

Use `ashaiy test --coverage` to measure Python statement and branch coverage,
including Python subprocesses. Reports and data live under `.cache/coverage/`;
open `.cache/coverage/html/index.html` for missing branches. Each run clears old
measurements and preserves test failures in its exit status. Only the checkout's
`scripts/` sources are measured: scripts copied into isolated test repositories,
shell, Lean, and TeX are outside this report. Use it to locate gaps, without a
percentage gate or treating execution as proof of assertion quality.

Use `test_support.py` builders for valid fixture setup; keep malformed records
and expected results explicit. Register cleanup immediately, start long-lived
processes in new sessions, bound waits, and clean process groups before their
temporary directories.
`workflow_support.py` evaluates the workflow expressions used by tests; it does
not emulate Actions scheduling or implicit status checks.

`test_site_rendering.py` uses Jekyll to check HTML, metadata escaping, relative
links and PDF URL consistency. Playwright drives the installed Chromium to check
headings and panels at mobile, tablet, and desktop widths. It does not pin visual
spacing or screenshots. Run `ashaiy site test` to require the site toolchain;
CI runs this command in the selected toolchain image so missing browser tools fail.
Under `ashaiy test`, missing Jekyll or Chromium produces explicit skips.
Browser failures retain `build/test-results/site-layout-trace.zip`, uploaded by
CI; inspect it with `python3 -m playwright show-trace <path>`. Fixtures and Jekyll
output use temporary directories.
Lean audit and LaTeX rendering tests require their corresponding toolchains and
report skips when their prerequisite executables are absent. LaTeX fixtures live
in `fixtures/`; build output stays under ignored `build/` directories.
