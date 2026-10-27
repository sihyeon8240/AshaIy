# Automation design decisions

This guide records the reasons for the automation boundaries and the evidence
needed to change them as the collection grows. File ownership remains in
[architecture](ARCHITECTURE.md), commands in the [developer workflow](developer-workflow.md),
and operational reuse rules in the [maintainer guide](maintainer-guide.md).

## Patterns and their responsibilities

| Pattern | Current implementation | Benefit and boundary |
| --- | --- | --- |
| Manifest-driven architecture | The book registry and ordered contents/module manifests generate assembly and configuration consumers. | Adding books follows the same rules without another dispatcher branch. Generated files are projections, with drift checks against their source. |
| Facade and composition root | `scripts/ashaiy` and `scripts/cli/` coordinate specialized modules and external tools. | One supported interface owns selection and failure propagation; domain modules retain their validation rules. |
| Functional core with imperative coordination | Parsers, validators, renderers, and input descriptions build values; generators and scripts install files or execute tools. | Plans can be validated before writes and compared without compiling a book. Filesystem effects remain explicit. |
| Pipeline and lightweight Command | `Stage` holds a name and callable; `run_stages` invokes them in order and returns the completed prefix and first failure. | Invocation is separated from coordination with little machinery. Completion is scoped to one invocation. |
| Adapter and Strategy | Shell/Python boundaries adapt latexmk, Lake, Git, Jekyll, Docker, and GitHub; strict YAML uses the native parser when available with a Python fallback. | Established systems own their specialist work while repository-specific contracts stay local. |
| Invocation-scoped memoization | `SourceReads` and `MacroRepository` reuse source values while planning one operation. | Common manifests are parsed once; a later invocation sees edits. These are not persistent success caches or process-wide singletons. |
| Bounded worker pool | `build_all.py` limits active book processes and checks logs independently. | Memory use follows the configured worker count. Failed books do not suppress independent results; cancellation reaps process groups. |
| Guarded file updates | Source writers hold an advisory lock from reading through installation, check observed bytes, and replace individual files. | Cooperating writers avoid lost updates. Exception recovery preserves originals when restoration fails. |
| Conservative dependency analysis | Git changes, book ownership, static TeX references, and shared-input policy select affected books. | Unknown inputs select broadly. Runtime recorder traces can supplement this policy without making absent inputs disappear. |
| Layered build reuse | Per-book Git input digests seed latexmk state; verified artifacts separately bind the entire tree, image, environment, checksums, and CI provenance. | Incremental speed does not imply successful validation. Log checks remain mandatory. |

The code has no general publish/subscribe Observer system. Direct callbacks in a
pipeline and polling child processes do not create one. Add observers only when
several independent consumers need events with explicit ordering, failure, and
lifetime rules; current diagnostics and phase metrics do not need an event bus.

Manifest loaders construct validated data, but the code does not need a GoF
Factory Method or Abstract Factory hierarchy. Introduce one only when independent
implementations must create interchangeable families of objects. Adding another
textbook currently adds data, not another implementation family.

`Stage` already expresses the central Command intent: encapsulating an invocation
for an invoker. GoF Command does not require undo, serialization, or inheritance.
Concrete request objects would become useful for a persistent queue or execution
across processes. `BookInputs` deliberately describes cache inputs as immutable,
JSON-serializable data; it is not an executable command or a complete hermetic
build request. Saving completed stage names alone cannot safely resume work after
inputs change. Re-execution or input-and-policy validation is still required.

## Evidence for the current boundaries

The October 2026 review used baseline commit
`ff87320cd28fcf9f30c5cb264aa2ac427ef8a1c1`, Python 3.14.8, Linux ARM64,
10 logical CPUs, and approximately 8 GiB RAM. Synthetic repositories exercised
real manifest loading and generators with 100 sections per book. The following
times are warm-filesystem medians of three local runs, not hosted CI timings or
full textbook compilation costs.

| Books | Sections | Impact planning, seconds | Site projection, seconds |
| ---: | ---: | ---: | ---: |
| 3 | 300 | 0.032 | 0.030 |
| 10 | 1,000 | 0.103 | 0.099 |
| 30 | 3,000 | 0.315 | 0.304 |
| 60 | 6,000 | 0.639 | 0.611 |

At 60 books and 400 sections per book, planning took 1.960 seconds and site
projection 1.910 seconds. This supports keeping the directory/manifest design
for dozens of books; it does not predict Lean or TeX costs for 24,000 sections.

| Experiment | Observation | Decision |
| --- | --- | --- |
| Native strict YAML parser | The 123 repository YAML inputs had equivalent results. A 60-book macro pass fell from 0.782 to 0.240 seconds; site projection from 0.603 to 0.263 seconds. | Use the library's native parser with the existing duplicate/merge rules and a Python fallback. Reuse shared macro inputs within a plan. |
| Generic metadata validation | JSON Schema alone differed from domain validation on 6 of 99 cases, including duplicate identities and integer/version rules. | Keep schemas for editor assistance and domain validators for full semantics. |
| YAML round-trip editing | The candidate preserved semantics in all seven fixtures but changed outside-target text in two. | Retain targeted release edits; a parser replacement must satisfy source-preservation contracts. |
| Atomic writes and competing writers | A killed direct write left half a file. Replacement preserved the previous complete file, but replacement alone and write-only locks still lost competing updates. | Use same-filesystem replacement plus a read-plan-write lock and observed-byte checks. |
| Ninja scheduler | Sixty controlled short tasks took 3.072 seconds with the current scheduler and 2.463 with Ninja. An interrupt experiment left an ignoring descendant alive with Ninja. | Retain the scheduler's lifecycle contract. These tasks did not measure textbook compilation throughput. |
| Official artifact download Action | The pinned Action checked digests, but did not enforce the repository's custom expanded size/total deadline and cleanup policy. | Keep the shared bounded transfer layer used by PDF, image, and release reuse. |
| Recorder-only dependency selection | A previous `.fls` trace covered existing inputs but missed a newly added optional override. | Keep conservative static and absence/fallback handling. Do not use a prior trace as the sole cache contract. |
| Local content-addressed prototype | A source-comment edit changed the input action key while the reproducible PDF digest stayed identical. A corrupted output object was rejected. | Input identity and output identity are distinct. A remote result cache still needs a complete input model and provenance policy. |

Three actual textbook builds at worker limits 1, 2, and 4 took approximately
23.6, 17.0, and 10.4 seconds respectively, with summed process RSS samples of
338, 604, and 897 MiB. Only three books were active, so the last case did not
exercise four simultaneous compilers. Keep the worker count bounded and tune it
against real book sizes and available memory; book count is not a concurrency
setting.

The implemented reproducibility check forced two builds of each of the three
books into different output directories. Every strict log check passed and each
book's PDF SHA-256 and extracted-text SHA-256 matched across runs. The environment
used the pinned archive date, epoch `1789862400`, and the existing toolchain.
Final PDFs also matched the baseline's extracted text and all-page 45 DPI
grayscale raster output, checking that the automation changes preserved visible
content at that resolution.
This is evidence for that local environment, not a guarantee across architectures,
toolchain revisions, arbitrary local assets, or all future TeX packages.

Detailed experiments and raw measurements remain local under
`build/design-review-20261027/`, including `REPORT.md`, the evidence archive,
and `reproducibility-final/results.json`. They are disposable build outputs.
Regression tests retain the important safety and input-selection contracts.

## Content-addressed builds and atomicity

The incremental key uses committed paths, file modes, and Git object IDs for the
book and shared build directories. Committed `book.tex` is the generated
publication-metadata projection, so changing another book's title or registry
display order does not invalidate this book's incremental state. Shared scripts
and configuration remain conservative inputs. Dirty source builds still work
through latexmk; a committed Git fingerprint does not describe the dirty tree.

A full content-addressed result system would need separate action descriptors and
output blobs, declared tools/environment, negative dependencies, fallback search
semantics, corruption checks, and controlled execution. `SOURCE_DATE_EPOCH` is
part of that identity; an output digest alone cannot prove who built it or whether
its log passed. Keep the existing full-tree/provenance gate for verified PDF
reuse. Introduce a remote CAS or Bazel/Nix migration only after measuring enough
repeated expensive identical work to justify this additional contract.

Atomic replacement protects one filename's visibility. Advisory locking
coordinates cooperating writers. Content comparisons detect observed external
edits; external editors do not join the lock. Exception rollback provides
recoverability. Optional file/directory `fsync` requests durability for important
small source updates. None of these alone is a multi-file ACID transaction:
`SIGKILL` between replacements can leave complete files from different generations.
Regenerate and validate after such an interruption. If readers later require a
coherent generated directory generation, use immutable generation directories
and one reference switch, with readers pinning that generation once.

## Scaling CI from measurements

Book matrix jobs now record preparation, verified-reuse lookup, incremental cache
restore, image preparation, compilation, strict log checking, and artifact
publication. Failed commands keep their exit codes. Interrupted phases remain
incomplete in the report. See the
[measurement procedure](maintainer-guide.md#build-measurements).

Keep one book per job until a complete successful run selects at least 20 books
and measured preparation plus image handling accounts for at least 30% of the
measured job time. Then compare groups of 2–4 books per job. Adoption requires
at least 20% less measured runner time with at most 5% worse overall wall time,
while preserving book-level failures, artifact names, cancellation, and verified
provenance. These thresholds are an operating policy, not achieved savings.

The measurements start after checkout and exclude runner provisioning, queueing,
the upstream shared-image job, and the telemetry upload itself. Combine them with
GitHub job timestamps when evaluating full workflow costs. Hosted CI and cache
eviction were not measured during the local review. The grouping evaluator
recommends an experiment; it does not change the matrix or publication gates.
