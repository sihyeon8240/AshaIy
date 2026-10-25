# Lean formalization

This guide owns proof policy, prerequisites, Lean source layout, and checked-source
correspondence. The [writing guide](writing-guide.md#paired-mathematical-exposition-and-lean-code)
owns the presentation of mathematical explanation and Lean code.

## Authoring policy

Complete the Lean statement and kernel-checked proof before writing a new or
mathematically revised formalized theorem in LaTeX. Unrelated edits need not
convert unformalized material; motivation, history, and examples need Lean only
when selected for formalization. Typographical and presentation edits need no proof rewrite.

1. Write definitions, statement, and proof in the owning namespace, include the
   module in the `Textbooks` import closure, and run `ashaiy lean check`.
2. Write the statement from the checked declaration, preserving domains,
   quantifiers, hypotheses, conclusions, and implicit/typeclass assumptions.
   Use the [paired exposition format](writing-guide.md#paired-mathematical-exposition-and-lean-code).
3. Explain the verified mathematical reasoning, including supporting lemmas and
   automated steps that readers need to understand. A Mathlib citation alone is
   not a pedagogical proof: explain the argument or identify a cited prerequisite.
4. Add the LaTeX label and proof-index entry, then run the applicable
   [validation](CONTRIBUTING.md#validation-by-change-category).
5. Review statement and proof correspondence in both directions. If the intended
   mathematics changes, check Lean before revising the prose.

CI cannot establish authoring order or natural-language fidelity; contributors
and human reviewers remain responsible, including for AI-assisted exposition.

### Displayed-code correspondence

Displayed signatures and proof fragments must reproduce the owning `.lean`
declaration, allowing presentation-only indentation changes. Imports, namespace
context, and the declaration-to-proof connector may remain outside the fragments;
explain any necessary context. Fragments may depend on preceding fragments and
need not compile independently. Do not substitute unchecked proofs or omit
substantive reasoning.

Update displayed code with its checked source and manually review the statement,
each explanation/code pair, and complete declaration for agreement, including
display-only edits. `ashaiy lean check` neither extracts printed code nor checks
its correspondence; PDF compilation establishes only that it can be typeset.

## Lean readability

Use
[`DivisionAlgorithm.lean`](../lean/Textbooks/ElementaryNumberTheory/DivisibilityTheoryInTheIntegers/DivisionAlgorithm.lean)
as a layout reference. Separate mathematical reasoning units with one blank line:
setup, witness selection, local claims, cases, and conclusion. Keep tactics for
one local goal or short calculation together, including related `have`/`obtain`
steps; do not separate every tactic.

Indent each nested `by` proof and branch body by two spaces. Align sibling
`·` branches and named cases, and distinguish substantial branches with blank
lines. Wrap long declaration hypotheses and conclusions with four-space
continuations; wrap long applications, constructors, and rewrite lists at their
argument boundaries. Aim to keep lines within 100 characters.

Put named local proofs and multi-step inline proofs in indented blocks; retain
compact single-step arguments such as `by ring`. Preserve `<;>` goal behavior
when wrapping it. Align `calc` steps and indent supporting proofs beneath them.
Use brief comments for non-obvious reasons or constraints; let structure and
spacing show the argument.

Apply the same layout to displayed Lean under the
[source correspondence policy](#displayed-code-correspondence); the
[writing guide](writing-guide.md#paired-mathematical-prose-and-lean-code) owns
LaTeX placement. Formatting must preserve declarations, dependencies, and proof
steps. Use the [validation matrix](CONTRIBUTING.md#validation-by-change-category).

## Trust and dependency model

Lean's kernel checks the pinned project's proofs. The
[validation audit](#validation-commands) enforces the axiom trust boundary;
book policies separately delimit permitted mathematical prerequisites.

## Dependency policy

Book modules may import Mathlib and their own book's modules; direct cross-book
imports are rejected. Use Mathlib for shared results. If it lacks one, contribute
upstream when practical or keep separate book-local proofs. Do not create a
shared foundation or re-export layer merely to hide Mathlib names.

Thin wrappers may adapt Mathlib to a book's printed formulation, notation, or
name. Keep them in the owning namespace as stable proof-index declarations.

## Book-owned prerequisite boundaries

Each book owns its starting assumptions in `books/<slug>/formalization.md`,
including its logic and foundational principles. There is no common mathematical
prerequisite baseline. Books on foundations, including set theory, logic, and
model theory, specify the object theory they study separately from Lean's
metatheory. Implement accepted mathematical premises through checked results
or explicit hypotheses. Every book follows the repository's kernel trust boundary
and prohibition on unchecked axioms.

Start new book policies from the
[formalization boundary template](../common/templates/formalization.md), also
copied by `ashaiy book new`. Complete its prompts before formalization; the template
does not authorize any mathematical prerequisites.

Current book policies are:

- [Elementary Number Theory](../books/elementary-number-theory/formalization.md).
- [Linear Algebra](../books/linear-algebra/formalization.md).
- [Mathematical Analysis](../books/mathematical-analysis/formalization.md).

Policies contain starting structures, accepted results, core developments, and
scoped exceptions. Group routine facts by topic, naming individual results when
needed to delimit scope. Broad labels such as "basic algebra" must not authorize
core results or stronger theory. Keep API details and proof recipes beside their
declarations or exposition, and coverage in proof indexes; link here for shared rules.

Amend a policy with the first use of a substantive result outside its boundary:
state what is allowed, where, and why. Acceptance never transfers between books.

## Proof roles and permitted dependencies

A declaration's kind follows its LaTeX environment; its role governs permitted
proof dependencies. Roles guide review and are not [proof-index fields](#linking-a-verified-proof).

| Proof role | Permitted proof dependencies |
|---|---|
| Prerequisite | Direct Mathlib citation within the owning book's accepted boundary; document its role as an assumed result. |
| Core result | Accepted prerequisites and earlier established results of the same book, with permitted bookkeeping lemmas. |
| Supporting lemma | Reuse Mathlib for logical, representational, and elementary computational steps within the book's boundary; classify substantive new mathematics as a prerequisite or core result. |

### Dependency review

A core proof must not invoke the target's Mathlib counterpart, an equivalent
result, or an unaccepted stronger result that supplies the essential argument.
Judge a supporting lemma by the mathematics it supplies, not its name or length.
Alternative proofs using additional external theory must be labeled separately
and have their extra prerequisites recorded; they do not replace the core proof.

The intended bottom-up order is the book's mathematical dependency order, which
must be acyclic and consistent with its exposition. Reuse Mathlib's standard
structures and definitions rather than reconstructing their implementations.
This policy does not require every transitive implementation dependency inside
Mathlib to follow the textbook's chapter order.

Prefer focused imports, but imports alone do not establish compliance. Review
actual proof dependencies, including implicit typeclass assumptions and facts
used by simplification or search. Automation may discharge routine steps within
the accepted boundary; it must not conceal the core mathematical argument or
supply an unaccepted result. Use explicit lemmas or restricted automation such as
`simp only [...]` when needed to make the dependency boundary reviewable. No
particular tactic is universally authorized as mathematical background.

### Declaration documentation

For new or revised mathematical declarations, begin the Lean declaration
docstring with `Kind:` for proved statements and `Definition:` for
definitions. Use the capitalized LaTeX environment name as the kind:
`Theorem`, `Lemma`, `Proposition`, or `Corollary`. These kinds all use Lean
`theorem` declarations; Lean syntax does not determine the textbook kind.
When no corresponding textbook statement exists yet, choose the kind that
matches its intended exposition. Describe the mathematics without printed
textbook numbers or parenthesized proof-role tags. Keep textbook links in the
proof index using stable LaTeX labels. For example:

```lean
/-- Definition: the nonnegative greatest common divisor, with value zero
when both inputs are zero. -/
/-- Theorem: Bezout's identity for the locally constructed gcd. -/
/-- Lemma: an elementary representation conversion. -/
/-- Corollary: a consequence of an earlier local theorem. -/
/-- Proposition: an accepted result cited from Mathlib. -/
```

Proof roles and kinds are independent: a corollary may be core mathematics.
Explain dependency choices in prose where needed. Definitions, including
`noncomputable def`, must state their meaning and conventions; existence proofs
still require accepted prerequisites or earlier local results.

For a printed `axiom`, use `Axiom:` for explicit hypotheses, assumption fields,
or checked theorems, explaining the latter's presentation role. Never introduce
an unchecked Lean `axiom`. Other exposition environments do not automatically
require declarations; see [Authoring policy](#authoring-policy).

Module documentation may explain shared dependencies but does not replace these
prefixes. Apply them when declarations are next revised; unrelated sources need
no relabeling.

## Statements and citation policy

The checked Lean statement must faithfully match the textbook's domains,
quantifiers, hypotheses, and conclusion. Prefer Mathlib's standard definitions
and interfaces. When the intended statement has the same assumptions, conclusion,
and generality as an existing Mathlib theorem, prefer its statement shape;
identical syntax or proof implementation is not required. Do not generalize a
textbook theorem merely to match Mathlib, or silently strengthen assumptions
through typeclasses. Use a book-local specialization or wrapper when appropriate.
Cite earlier independently proved local declarations in subsequent core proofs.
For accepted external prerequisites, cite Mathlib directly or use a thin
book-local wrapper under the [dependency policy](#dependency-policy).
Review those citations under [Dependency review](#dependency-review).

Retain independent proofs even when Mathlib contains the same result. Do not add
declarations, counterpart inventories, or comments solely to compare local
constructions or proofs with Mathlib equivalents. Keep declaration comments
concise: identify the mathematical role and essential hypotheses. Explain
accepted prerequisites and scoped exceptions at their use sites when needed;
record their permitted scope in the [book policy](#book-owned-prerequisite-boundaries).

## Mathematical language and standard interfaces

Analysis and algebra books may retain ordinary classical set-and-function
language while using Lean's type-theoretic foundations. Represent an ambient
space by a type, its subsets by `Set`, a subset used as a space by its subtype,
and indexed families by functions. This is not a formalization of the ZFC axiom
system or an identification of types with sets in a ZFC universe. Books studying
foundations must specify their object theory separately.

Prefer standard Mathlib structures, predicates, and operations in statements.
Explain their elementary characterizations in the textbook instead of creating
parallel definitions solely to reproduce printed notation. Define a collection
such as `{U : Set X | IsOpen U}` only when the collection itself is needed.
Keep ball notation distinct from general neighborhood notation.

A local construction is justified when its construction is part of the lesson
or the textbook convention differs. Preserve empty cases and explicit
hypotheses, and use the local construction and its proved properties in later
developments. Adopting a standard definition does not permit
replacing a core proof by its Mathlib counterpart. Establish substantive
characterizations locally when they are part of the book's mathematical content.

## Declaration naming

Follow [Mathlib naming conventions](https://leanprover-community.github.io/contribute/naming.html):
theorem names use `snake_case`, ordinary definitions use `lowerCamelCase`, and
types and structures use `UpperCamelCase`, subject to Mathlib's detailed rules
such as retaining the spelling of a definition embedded in a theorem name.
Keep declarations under `<Book>.ChapterName`, where `<Book>` is the registered
`lean_module` and `ChapterName` is the entry's stable `lean_namespace` in
`chapters.yml`. Appendices use `<Book>.Appendices.AppendixName`, with the same
manifest field supplying `AppendixName`. Reading order does not affect names. Do not
include `Textbooks` in declaration namespaces. Definitions and reusable lemmas
belong to their owning chapter too; use `private lemma` for helpers needed only
inside one file. Topic filenames do not add a required namespace level.
Use mathematical names rather than printed theorem numbers. Prefer the Mathlib
basename for a matching statement when it fits the local namespace; otherwise
name the actual hypotheses and conclusion. Avoid temporary names such as `my_`,
`textbook_`, `_proof`, or `_v2` as substitutes for mathematical meaning.

Apply these rules to new declarations. Rename existing declarations when they
are next revised for formalization, updating all uses and proof-index entries
together; documentation-only policy changes need not rename checked declarations.

## Source layout

Before adding a book's first Lean source, complete its
[prerequisite policy](#book-owned-prerequisite-boundaries), then:

1. Set a unique UpperCamelCase `lean_module` in its `config/books.yml` record.
2. Set the chapter or appendix's stable `lean_namespace` in `chapters.yml`.
3. Create topic sources and a `modules.yml` in the matching directory below.
4. Run `ashaiy generated generate --book <slug>`, then `ashaiy lean check`.

| Path under `lean/` | Role |
|---|---|
| `Textbooks.lean` | Generated project aggregation |
| `Textbooks/<Book>/All.lean` | Generated book aggregation |
| `Textbooks/<Book>/ChapterName/<Topic>.lean` | Chapter mathematics, including its first result |
| `Textbooks/<Book>/Appendices/AppendixName/<Topic>.lean` | Appendix mathematics |

Use descriptive UpperCamelCase ASCII topic filenames with letters and digits.
Group related definitions, helpers, and core results by mathematical topic; one
substantial theorem may fill a topic. Split by distinct responsibilities or
imports, not line count. Aggregation files contain no mathematical declarations
and must not be hand-edited. `All.lean` is the only book-level Lean file.

Register topic filenames without extensions in each chapter or appendix's
`modules.yml`, in reading order:

```yaml
schema_version: 1

modules:
  - DivisionAlgorithm
  - GreatestCommonDivisor
```

Regenerate after adding, removing, or reordering topics. Chapter and appendix
order comes from `chapters.yml`; each formalized entry declares its stable
`lean_namespace` there. Names must be unique within each list
and use UpperCamelCase ASCII letters and digits. `All`, `Appendices`, and the
numbered forms `ChapterNN` and `AppendixNN` are reserved. Keep filenames stable
when changing reading order. No manifest is needed for a chapter without
a Lean directory; an existing empty directory may use `modules: []`.
Import required results explicitly inside topic sources; these imports determine
dependencies and must remain acyclic. Do not create empty topic placeholders.
See the [architecture contract](ARCHITECTURE.md) for
manifest validation and generated-file ownership.

Module paths and declaration namespaces are separate. For example,
`import Textbooks.ElementaryNumberTheory.DivisibilityTheoryInTheIntegers.DivisionAlgorithm` loads
results declared in `namespace ElementaryNumberTheory.DivisibilityTheoryInTheIntegers`. Retain
`Textbooks` in filesystem paths and imports, but not in declaration names.
Moving a declaration between topic files within a chapter must preserve its
public name and proof-index link.

Use textbook sections as the default topic boundaries without requiring one
Lean file per section. Proof-link checks enforce registered declarations' path
and namespace shape; reviewers assess topic coherence and unregistered names.

`lean/lakefile.toml` sets `autoImplicit = false` project-wide. Check the global
Lean options before adding module-local settings; do not repeat those defaults.
Do not use `sorry`, `admit`, or new unchecked `axiom` declarations in checked
sources.

## Linking a verified proof

A verified LaTeX theorem needs two parts:

1. A repository-global theorem label such as `ma:thm:compactness`.
2. An entry in the matching chapter or appendix shard below naming its Lean
   proof declaration.

Each shard is owned by one registered book and one chapter or appendix:

| LaTeX source directory | Proof-index shard | Lean namespace |
|---|---|---|
| `books/<book>/chapters/topic/` | `books/<book>/chapters/topic/proofs.yml` | `<Book>.Topic` |
| `books/<book>/appendices/topic/` | `books/<book>/appendices/topic/proofs.yml` | `<Book>.Appendices.Topic` |

Every registered chapter and appendix owns a `proofs.yml`, including `proofs: []`
when no results are registered. The loader follows `config/books.yml` and `chapters.yml`
order and rejects missing files or indexes outside registered directories.
Run `ashaiy contents generate --book <slug>` to initialize missing files without replacing
existing entries.

Both shard kinds use the same entry schema:

```yaml
proofs:
  - id: ma:thm:compactness
    declaration: MathematicalAnalysis.BasicTopology.compactness
```

Use the actual checked declaration and label. Entries contain only `id` and
`declaration`; the shard path supplies ownership. Do not repeat `book`, `chapter`,
`kind`, or `tex` paths.
Labels must belong to a `theorem`, `lemma`, `proposition`, or `corollary`
environment within that shard's source directory. A theorem-like label on a
section, definition, equation, or literal code sample is not a verified result.
Labels and declarations must be unique across both kinds of shard.
Register only results already present in these LaTeX environments. Keep Lean-only
helper results in the Lean sources without proof-index entries until they have
a corresponding textbook result.

Appendix proofs follow the same book policies and review requirements; include
them in its generated aggregation and reuse earlier results within that book.

## Validation commands

```sh
ashaiy check proof-links
ashaiy lean build
ashaiy lean check
ashaiy check all --strict
```

`ashaiy check proof-links` checks ownership, theorem environments, unique labels
and declarations, namespace/module paths, import reachability, and source-level
`sorry`, `admit`, and `axiom` markers outside comments and literals. It runs
without Lean and reports registered links, not kernel verification.

`ashaiy lean check` builds the pinned project and runs those checks plus a Lean
environment audit after `import Textbooks`. Each registered declaration must
exist, be safe, and have a proposition as its type. The audit rejects
repository-defined axioms, including private and unused axioms and declarations
in the root module. It also checks the transitive axiom dependencies of all
imported textbook declarations, including unregistered helpers. Only Lean's
standard `propext`, `Classical.choice`, and `Quot.sound` axioms are permitted;
`sorryAx` and other added axioms are rejected. This metatheory allowlist does not
authorize mathematical prerequisites outside a book's boundary.

[`lean-proof-audit.lean`](../scripts/lean/lean-proof-audit.lean) is validation
tooling; its generated probe lives in ignored `build/lean-links/`. Source scanning
also catches unfinished anonymous examples absent from the imported environment.
`ashaiy check all --strict` requires these checks before building PDFs.

Formal checks do not establish natural-language fidelity, displayed-code
correspondence, prerequisite compliance, or bottom-up proof order. Review these
under the [authoring policy](#authoring-policy).

## Dependency updates

Change `LEAN_VERSION` and `LEAN_TOOLCHAIN` together in `config/toolchain.env`,
then run `ashaiy config generate` to synchronize `lean/lean-toolchain` and the
Mathlib release in `lean/lakefile.toml`. Do not edit generated values directly.
Run `lake update` inside `lean/`, review `lean/lake-manifest.json`, and regenerate
configuration to refresh the shared preface's resolved Mathlib version and commit.
Run `ashaiy config check`, `ashaiy lean check`, and the
[shared-dependency checks](CONTRIBUTING.md#validation-by-change-category).
Commit configuration, synchronized consumers, and the lock together. Ordinary
checks must not run `lake update`.

## Scope and coverage

Do not claim that an entire textbook is formally verified merely because the
Lean project builds. Coverage counts textbook theorem, lemma, proposition, and
corollary environments linked through chapter and appendix `proofs.yml` files,
once per environment, relative to all such environments in the book. Lean-only
results, comments, and literal code samples are excluded; unlabeled environments
remain in the denominator. Multiple labels never count a result more than once,
so coverage cannot exceed 100%.
