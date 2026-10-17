# Lean formalization

The repository distinguishes independent publication from formal dependency.
Every PDF is assembled from its owning directory. Lean modules depend on the
pinned Mathlib revision and use their textbook's namespace.

## Authoring policy

For new or mathematically revised theorems selected for formalization, complete
the Lean statement and kernel-checked proof before writing or revising their
natural-language statement and proof. Lean is the reference for definitions,
hypotheses, conclusions, and the verified reasoning; LaTeX owns the educational
exposition and presentation.

This workflow applies to new or mathematically revised formalized results.
Unformalized material need not be converted as part of unrelated edits.
Motivation, historical notes, and illustrative examples do not require Lean
counterparts unless they are themselves selected for formalization. Typographical
and presentation-only changes do not require rewriting a Lean proof.

1. Write the needed definitions, theorem, and proof in the owning book's Lean
   namespace, include the module in the `Textbooks` import closure, and run
   `ashaiy lean check`. Use a book-local wrapper when the printed formulation
   differs from Mathlib.
2. Write the natural-language statement from the checked declaration. Preserve
   variable domains, quantifiers, hypotheses, and conclusions, including relevant
   implicit and typeclass assumptions. Explain prerequisite definitions and use
   the [paired exposition format](writing-guide.md#paired-mathematical-exposition-and-lean-code).
3. Write an educational proof grounded in the verified reasoning. Explain the
   mathematical steps and supporting lemmas rather than translating tactics
   line by line. Expand automated steps when readers need the explanation.
   Calling a Mathlib theorem alone does not supply a pedagogical proof: explain
   the required reasoning or identify the result as a cited prerequisite.
4. Add the LaTeX label and matching chapter or appendix proof-index entry, then rerun
   `ashaiy lean check` and the affected textbook's build and log checks. Complete
   the repository validation required before review.
5. Review the correspondence in both directions: the prose must express the
   checked statement faithfully, and every substantive proof step must be
   justified within the verified assumptions. If the intended mathematics
   changes, update and check Lean before revising the prose.

CI checks proofs and registered links; it cannot establish authoring order or
the fidelity of a natural-language translation. Contributors and human reviewers
remain responsible for those requirements, including AI-assisted exposition.

### Displayed-code correspondence

The complete declaration and proof in the owning `.lean` module are the checked
formal source. Code displayed in LaTeX must reproduce the corresponding
signature and proof fragments from that source, allowing presentation-only
indentation changes. Imports, namespace context, and the declaration-to-proof
connector may remain outside the displayed fragments; make any context needed
to understand them clear. Do not substitute an unchecked alternative proof or
silently omit substantive reasoning from the displayed sequence.

Update displayed code together with changes to the corresponding Lean source.
Review the natural-language statement, each explanation/code pair, and the
complete checked declaration for agreement. A proof fragment can depend on
previous fragments and need not compile independently.

`ashaiy lean check` checks the Lean project and registered proof links; it does not
extract or compile code printed in LaTeX or establish that copied fragments
match the checked source. A successful PDF build only establishes that the
code can be typeset. Contributors and reviewers must check this correspondence
explicitly, including when only the displayed code changes.

## Lean readability

Use the division-algorithm proof in
[`DivisionAlgorithm.lean`](../lean/Textbooks/ElementaryNumberTheory/DivisibilityTheoryInTheIntegers/DivisionAlgorithm.lean)
as a layout reference. Group a proof by mathematical reasoning units: setup,
witness selection, local claims, case analysis, and the final conclusion.
Separate these units with one blank line. Keep consecutive tactics that perform
one short calculation together; do not insert a blank line after every tactic.

Place a blank line where the subgoal or the purpose of the argument changes.
Keep introductions, representation conversions, and short calculations for the
same local goal together. Related `have` claims or `obtain` steps may form one
unit; do not separate every declaration mechanically. For example, the interval
compactness proof first establishes the prerequisites for the supremum, then
locates it in the interval:

```lean
  have hne : T.Nonempty := ⟨a, ha⟩
  have hb : BddAbove T := ⟨b, fun x hx => hx.1.2⟩

  let c := sSup T
  have hac : a ≤ c := le_csSup hb ha
  have hcb : c ≤ b := csSup_le hne (fun x hx => hx.1.2)
```

Indent each nested `by` proof and branch body by two spaces. Align sibling
`·` branches and named cases, and distinguish substantial branches with blank
lines. Wrap long declaration hypotheses and conclusions with four-space
continuations; wrap long applications, constructors, and rewrite lists at their
argument boundaries. Aim to keep lines within 100 characters.

Put named local proofs on multiple lines. Expand multi-step inline proofs into
indented tactic blocks, while retaining compact single-step arguments such as
`by ring`. Preserve the goal behavior of `<;>` when wrapping it. Keep `calc`
steps aligned and their supporting proofs indented beneath the relevant step.
Comments should briefly explain a non-obvious reason or constraint; use proof
structure and spacing rather than long comment blocks to show the argument.

Apply this layout to displayed Lean under the
[source correspondence policy](#displayed-code-correspondence). The
[paired-code layout guidance](writing-guide.md#paired-mathematical-prose-and-lean-code)
owns LaTeX placement and page-break review.
Formatting is not a reason to change declarations, dependencies, or proof steps.
Run `ashaiy lean check`, `ashaiy check source`, and the affected books' strict builds;
when displayed code changes, also run `ashaiy format tex --check`.

## Trust and dependency model

The checked proof chain is:

```text
Lean kernel
  -> pinned Lean and Mathlib versions
  -> one textbook namespace
```

## Dependency policy

Book modules may import Mathlib and modules owned by the same book. Direct
imports from another textbook are rejected. When another textbook has already
formalized a needed mathematical result, use the corresponding Mathlib
declaration instead of importing that textbook. If Mathlib does not yet contain
the reusable result, contribute the general result upstream when practical or keep
separate book-local proofs; do not introduce a cross-book dependency.

Each book may keep a thin wrapper theorem when its printed formulation, notation,
or theorem name differs from Mathlib. Those wrappers remain in the owning book
namespace and provide stable declarations for proof-index entries. Do not create
a repository-local shared foundation or re-export layer merely to hide Mathlib
names.

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

Each policy records starting structures, accepted results, results developed in
the book, and scoped external exceptions. Keep it concise and organize accepted
background by mathematical topic. Name individual results when needed to draw a
significant boundary, rather than listing every routine set operation or
arithmetic helper. Broad labels such as "basic algebra" alone are insufficient
when they leave unclear whether a core result is already assumed.

Preserve the accepted scope when simplifying a policy. Link to this guide for
common proof and interface rules; keep Lean API names, representation details,
and proof recipes beside the relevant declarations or in the exposition. Record
verified coverage in proof indexes, not in prerequisite policies.

Before using a substantive external result outside the recorded boundary, amend
the owning policy and review that amendment together with its first use. An
exception must identify the result, where it is allowed, and why it is needed.
Acceptance in one book does not authorize use in another.

## Proof roles and permitted dependencies

Distinguish a declaration's textbook kind from its proof dependency role.
The kind follows the corresponding LaTeX environment; the role records which
mathematical dependencies its proof may use. Proof roles guide review and are
not fields in the [proof index](#linking-a-verified-proof).

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

Proof roles govern dependency review rather than docstring formatting: a
corollary may be a core result, and a statement printed as a theorem may serve
as a supporting lemma. Explain accepted prerequisites and dependency choices
in ordinary prose where needed; no role tag is required.
Definitions, including `noncomputable def` declarations, introduce mathematical
objects, relations, or constructions. State their meaning and conventions;
classify their proved properties separately. A construction requiring an
existence proof must use accepted prerequisites or earlier local results.
The `Definition:` label does not authorize additional assumptions or external
theorems.

For the LaTeX `axiom` environment, preserve the textbook kind with `Axiom:`
when documenting an explicit hypothesis or a structure's assumption field.
If the statement is instead proved from the accepted boundary, use
`Axiom:` on that theorem and explain that it is an axiom only in the
textbook presentation. Never translate the environment into a new unchecked
Lean `axiom` declaration. Follow the repository's proof-safety requirements and the book's prerequisite
boundary. Other exposition environments, such
as examples and remarks, do not automatically require Lean declarations; see
[Authoring policy](#authoring-policy).

Module documentation may explain shared prerequisites and dependency choices,
but does not replace these declaration prefixes for new or revised declarations.
Apply the convention when declarations are next revised; unrelated existing
sources need not be relabeled as part of a documentation change.

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

Before adding a book's first Lean source:

1. Set a unique UpperCamelCase `lean_module` in its `config/books.yml` record.
2. Set the chapter or appendix's stable `lean_namespace` in `chapters.yml`.
3. Create topic sources and a `modules.yml` in the matching directory below.
4. Run `ashaiy generated generate --book <slug>`, then `ashaiy lean check`.

Book creation supplies LaTeX sources and a prerequisite-policy template; it does
not register a Lean module. Complete that policy before formalizing results.

```text
lean/
  lean-toolchain
  lakefile.toml
  lake-manifest.json
  Textbooks.lean
  Textbooks/
    ElementaryNumberTheory/
      All.lean
      DivisibilityTheoryInTheIntegers/
        modules.yml
        DivisionAlgorithm.lean
```

Every mathematical source uses
`lean/Textbooks/<Book>/ChapterName/<Topic>.lean`, including a chapter's first
result. Appendix sources use
`lean/Textbooks/<Book>/Appendices/AppendixName/<Topic>.lean`. Use descriptive
`UpperCamelCase` topic filenames with ASCII letters and digits. Do not create a flat `ChapterName.lean` or adopt
one file per numbered theorem. Group related definitions, supporting lemmas,
and core results by mathematical topic; one substantial theorem may constitute
an entire topic. Split a topic when its mathematical responsibilities or import
dependencies become distinct, not at an arbitrary line count.

The root `Textbooks.lean` and each book's `All.lean` are aggregation entry points,
not homes for mathematical declarations. The book-level `All.lean` is the only
exception to the chapter/topic or appendix/topic layout under a book directory.
Both aggregation entry points are generated; do not edit them by hand.
Register topic filenames without extensions in the chapter or appendix
`modules.yml`, in reading order:

```yaml
schema_version: 1

modules:
  - DivisionAlgorithm
  - GreatestCommonDivisor
```

Run `ashaiy generated generate --book <slug>` after adding, removing, or reordering topics.
Chapter and appendix order comes from the book's `chapters.yml`; each formalized
entry declares its `lean_namespace` there. Names must be unique within each list
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

Use textbook sections as the default guide for topic boundaries. When a section
forms one coherent topic, prefer one Lean file for it. Keep shared definitions
and lemmas together or separate topics when their responsibilities or imports
require it; Lean files need not match LaTeX section files one-to-one.
Proof indexes link labeled theorems to declarations. Use mathematical
declaration names rather than printed theorem numbers. The proof-link checker enforces the
chapter/topic path shape and the registered declaration's book and chapter
namespace; human review checks whether a topic grouping is mathematically
coherent and whether unregistered declarations follow the namespace policy.

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

This is a schema example; use the actual checked declaration and label. The
shard path owns its book, chapter or appendix, and kind. Entries contain only
`id` and `declaration`; do not repeat `book`, `chapter`, `kind`, or `tex` paths.
Labels must belong to a `theorem`, `lemma`, `proposition`, or `corollary`
environment within that shard's source directory. A theorem-like label on a
section, definition, equation, or literal code sample is not a verified result.
Labels and declarations must be unique across both kinds of shard.
Register only results already present in these LaTeX environments. Keep Lean-only
helper results in the Lean sources without proof-index entries until they have
a corresponding textbook result.

Appendix proofs use the same book prerequisite policy, proof roles, import
boundary, and review requirements as chapter proofs. Include appendix modules
in the owning book's `All.lean`; earlier results within that book may be reused.

## Validation commands

```sh
ashaiy check proof-links
ashaiy lean build
ashaiy lean check
ashaiy check all --strict
```

`ashaiy check proof-links` is a fast structural and source check without Lean. It
checks shard ownership, theorem environments, unique labels and declarations,
namespace and module paths, import reachability, and source-level `sorry`,
`admit`, and `axiom` markers. Comments and literals are excluded from that marker
check. Its result reports registered links, not kernel verification.

`ashaiy lean check` builds the pinned project and runs those checks plus a Lean
environment audit after `import Textbooks`. Each registered declaration must
exist, be safe, and have a proposition as its type. The audit rejects
repository-defined axioms, including private and unused axioms and declarations
in the root module. It also checks the transitive axiom dependencies of all
imported textbook declarations, including unregistered helpers. Only Lean's
standard `propext`, `Classical.choice`, and `Quot.sound` axioms are permitted;
`sorryAx` and other added axioms are rejected. This metatheory allowlist does not
authorize mathematical prerequisites outside a book's boundary.

The audit implementation is `scripts/lean-proof-audit.lean`, validation tooling
rather than a textbook module. The Python adapter copies it and the registered
proof requests into ignored `build/lean-links/ProofLinks.lean`. Source scanning
also catches unfinished anonymous examples that do not leave a named declaration
in the imported environment. `ashaiy check all --strict` requires these checks before
building PDFs.

A passed gate establishes these formal and structural checks, not natural-language
fidelity or agreement of code copied into LaTeX. Review hypotheses, conclusions,
reasoning, and [displayed-code correspondence](#displayed-code-correspondence)
explicitly. Accepted mathematical prerequisites and the bottom-up proof order
also remain review obligations.

## Dependency updates

Dependency updates are intentional maintenance tasks. Change `LEAN_VERSION` and
`LEAN_TOOLCHAIN` together in `config/toolchain.env`, then run `ashaiy config generate`.
This synchronizes `lean/lean-toolchain` and the Mathlib release in
`lean/lakefile.toml`; do not edit those generated values directly. Run
`lake update` inside `lean/`, review `lean/lake-manifest.json`, then run
`ashaiy config generate` again to refresh the shared preface's resolved Mathlib version and
commit. Run
`ashaiy config check` and `ashaiy lean check`. Apply the shared-dependency validation
requirements in [Contributing](CONTRIBUTING.md#validation-by-change-category).
Commit the canonical configuration, synchronized consumers, and dependency lock
together. Ordinary checks must not run `lake update`.

## Scope and coverage

Do not claim that an entire textbook is formally verified merely because the
Lean project builds. Coverage counts textbook theorem, lemma, proposition, and
corollary environments linked through chapter and appendix `proofs.yml` files,
once per environment, relative to all such environments in the book. Lean-only
results are excluded.
For mathematics supplied by Mathlib, follow the
[book-owned prerequisite boundary](#book-owned-prerequisite-boundaries) and
[citation policy](#statements-and-citation-policy).
