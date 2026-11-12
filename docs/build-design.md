# Automation design decisions

[Architecture](ARCHITECTURE.md) owns file boundaries, the
[developer workflow](developer-workflow.md) owns commands, and the
[maintainer guide](maintainer-guide.md) owns publication and recovery.
This guide records decisions and the evidence needed to reconsider them.

## Patterns and responsibilities

| Decision | Reason | Reconsider when |
| --- | --- | --- |
| Ordered manifests generate assembly and configuration | Books add data instead of dispatcher branches; drift is checked | Metadata planning becomes a measured bottleneck |
| Python facade, functional validation and explicit side effects | Specialist tools retain builds/proofs; plans can be inspected before writes | Another implementation demonstrates material end-to-end gains |
| Small stages and adapters | Ordering, selection and failures are explicit | Persistent/distributed execution needs durable requests and input identity |
| Invocation-scoped source reuse | Shared inputs are read once without stale process-wide success state | Measurements justify a stronger snapshot model |
| Bounded workers with process-group cancellation | Concurrency and descendant lifetime stay controlled | A replacement preserves lifecycle guarantees and improves real workloads |
| Temporary test logs and bounded queued work | Completed output does not grow parent memory with total logs | Different consumers need streaming output values |
| Strict YAML plus semantic domain validation | Native parsing is fast; schemas alone cannot express all repository contracts | A replacement preserves duplicate/merge rules and source edits |
| Conservative dependency analysis | Unknown and newly present optional inputs remain safe | A more precise model covers absence and fallback semantics |
| Separate incremental caches and verified artifacts | Input/cache identity is not proof of successful validation | A remote result cache has complete input, environment and provenance contracts |

An event bus or factory hierarchy has no current consumer requirement. A new
compiled launcher adds a toolchain to maintain; earlier measurements found no
material test-suite gain. Keep shared configuration small and let consumers
project their required formats rather than introduce a general configuration DSL.

## Content-addressed builds and atomicity

Incremental keys bind committed paths, modes and Git objects. Generated
`book.tex` projects publication metadata without invalidating every book for an
unrelated registry record. Dirty local builds still use latexmk; committed keys
do not describe uncommitted inputs. Verified reuse separately binds the full
source tree, immutable image, environment, run/attempt and output checksums.
Unknown TeX inputs select conservatively; old recorder traces are supplementary.

Source updates use read-plan-write advisory locking, observed-byte comparisons,
same-filesystem replacement and exception rollback. External editors do not join
the lock. Individual replacements are atomic; multiple replacements are not a
crash transaction. Regenerate after abrupt termination. If readers later require
whole-directory coherence, compare immutable generations plus one reference
switch, with each reader pinning a generation.

## Reproducible measurements

Run in the pinned development image:

```sh
python3 scripts/repository/benchmark.py
python3 scripts/repository/benchmark.py --include-checks --repeats 3
```

The harness builds disposable 3/10/30/60-book repositories with 100 sections per
book and exercises real planning, macro and site generators. It also measures
64MiB of process output with file spooling. Optional checks compare one/four test
workers and isolated cold/warm formatter caches. Reports and logs go under
ignored `build/benchmarks/`; `--output` selects another location.

Reports record revision, dirty state, interpreter/platform, wall/CPU time and
20ms sampled process-tree RSS. RSS can double-count shared pages and miss short
peaks. Synthetic manifests do not predict compilation of large textbooks. Cold
formatter caches do not imply cold filesystem caches. Reproduce old published
comparisons from their source revision; historical local-only experiments are
supporting evidence, not a current performance contract.

Use [workflow measurements](maintainer-guide.md#workflow-cost-and-dependency-reports)
for checkout/provisioning, image transport, artifact sizes and cache usage.
Separate typical edits from image candidates and compare repeated runs. A local
image's installed size, directory usage and compressed archive size are distinct.
Current PDF/dev image separation and minimal TeX closure avoid shipping Lean and
browser tools to PDF-only jobs. Package inventories record actual resolved tools.

## Scaling CI from measurements

Keep one book per job until a complete successful run selects at least 20 books
and measured preparation plus image handling accounts for at least 30% of the
measured job time. Then compare groups of 2–4 books per job. Adoption requires
at least 20% less runner time with at most 5% worse overall wall time, preserving
book failures, artifact identity, cancellation and verified provenance.

Book phase reports start after checkout and contain nested stages; do not sum
nested durations. The workflow collector includes all job timestamps and reports
observed runner seconds separately from elapsed time and billing. Start delay
includes dependency waits, not just runner queueing.

Full-history source checkouts use `blob:none` filtering so ancestry and tags
remain available without downloading every historical PDF blob. Snapshot
checkout still needs current PDFs. Monitor history, cache churn and artifact
bytes before moving snapshots to another store or changing retention. Candidate
PDF bundles are currently downloaded per book; compare book-specific artifacts
or aggregation only when transfer costs justify their added orchestration.
Manual deployment retries remain available, including after unrelated pushes.

## Optional authoring and accessibility features

Keep macro declarations as the shared source for TeX packages and formatter
signatures. Add chapter/section scaffolding only after recurring authoring errors
justify it; preserve one source per logical section, stable labels and absent
local-only presentation assets. Do not create empty Lean topics automatically.

Displayed-code source links are an opt-in pilot under the
[formalization policy](formalization.md#displayed-code-correspondence).
They catch fragment drift, not mathematical meaning or proof completeness.
Website search/filtering is conditional on a larger catalog. PDF tagging is a
separate rendering experiment; strict compilation and visual quality alone do
not establish accessible reading order, usable mathematical semantics or a
PDF/UA conformance claim.

Run the optional structural tagging experiment with:

```sh
python3 scripts/latex/tagging_probe.py --install-missing
```

Additional packages come from the pinned TeX archive into ignored
`build/tagging-texmf/`, leaving the image and ordinary book builds unchanged.
The specimen, PDF, strict-log result and tagging warnings are recorded under
`build/tagging-probe/`. The current style can produce a tagged PDF, but tagpdf
reports that MathML generation is unavailable without unicode-math or
lua-unicode-math. This is an explicit boundary of the pilot, not a reason to
suppress the warning or claim mathematical accessibility. A typography change
requires a separate compatibility/assistive-technology study and shared checks.
