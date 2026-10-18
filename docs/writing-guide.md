# Textbook writing guide

This guide describes the repository's supported authoring interface. Structural
instructions protect the build and generated sources and are requirements. The
paired exposition format below is required for new or mathematically revised
theorems selected for formalization. Other prose and proof-layout conventions
are recommendations: prefer them for consistency, but depart from them when
another form is clearer in context.

Follow the [Lean-first authoring policy](formalization.md#authoring-policy)
before applying the paired exposition format in this guide.

## Book structure and manifests

### Creating and registering a book

Create and register a book from the repository root with:

```sh
ashaiy book new --slug <slug> --title "<title>"
```

The script copies `common/templates/`, creates the first chapter and section,
and registers the book in `config/books.yml`. The lower-level `books.py add` command
only registers an existing directory. After creation, run:

```sh
ashaiy config generate
ashaiy config check
```

Review and commit the new sources, `config/books.yml`, and synchronized
`.vscode/tasks.json` together. Complete the applicable
[validation checks](CONTRIBUTING.md#validation-by-change-category) before review.

The scaffold includes `formalization.md` from the
[formalization boundary template](../common/templates/formalization.md).
Complete its book-specific starting assumptions, accepted results, core
developments, and external exceptions before adding formalized results. Keep
Lean comments concise under the
[citation policy](formalization.md#statements-and-citation-policy). The template
supplies no common mathematical prerequisites.

### Generated assembly and section files

`book.tex` and chapter/appendix `index.tex` are generated assembly. Write each
logical section's body in exactly one `section-name.tex`, without `\chapter`,
`\section`, or package loads.

Keep slugs stable when changing titles or reading order. Set a stable
UpperCamelCase `lean_namespace` before adding a chapter or appendix's Lean
sources. See [assembly ownership](ARCHITECTURE.md#book-assembly-and-file-responsibilities)
and [naming](ARCHITECTURE.md#naming-conventions).

### Contents manifests and metadata

Edit the `chapters` and optional `appendices` lists in `chapters.yml` and
their `sections.yml` files, then run `ashaiy contents generate --book <slug>`. Do not edit
the generated `book.tex` or any chapter `index.tex`. Chapter and section titles
may contain LaTeX, including `\texorpdfstring` where a PDF-safe form is required.

The `sections` and `all` scopes also initialize missing chapter and appendix
`proofs.yml` files from [the proof-index template](../common/templates/proofs.yml).
Existing files are preserved; maintain their entries by hand. The `check` mode
reports missing files without creating them. New books use this same initialization.

Use meaningful ASCII slugs: preserve mathematical identifiers
and exponents (for example, `functions-of-class-l2` and `the-number-e`) instead
of deriving a lossy slug from rendered title text.

Edit manifest-owned metadata in `config/books.yml`, then run
`ashaiy contents generate --scope chapters --book <slug>` to regenerate `book.tex`. Field ownership and
optional frontmatter overrides are defined in the
[architecture guide](ARCHITECTURE.md#metadata-and-automation).

For example, to add a chapter to an existing book, append this entry to its
`chapters.yml` under `chapters`:

```yaml
  - slug: vector-spaces
    title: Vector Spaces
    lean_namespace: VectorSpaces
```

Create `chapters/vector-spaces/sections.yml` with:

```yaml
schema_version: 1
sections:
  - slug: linear-combinations
    title: Linear Combinations
```

Write the section body in `chapters/vector-spaces/linear-combinations.tex`,
then run from the repository root:

```sh
ashaiy contents generate --book <slug>
ashaiy contents check  --book <slug>
ashaiy format tex --check
ashaiy check source
ashaiy book build --book <slug> --check --strict
```

Use a chapter slug not already registered in that book. For a section in an
existing chapter, add only its `sections.yml` entry and source file, then use
the same commands. Review and commit the manifests, sources, generated assembly,
and initialized proof index together.

### Authoring and style files

Section files do not load packages directly; `book.tex` loads the shared
`textbook` package and optional book-local `overrides/style.sty` extensions.

Files such as `context.tex` containing AI question context are authoring aids,
not PDF inputs. Do not add them to the build graph.

## LaTeX document structure

### Theorem environments

The public environments are `axiom`, `theorem`, `lemma`, `proposition`,
`corollary`, `definition`, `example`, `exercise`, `problem`, `solution`,
`remark`, and `proof`. Use `axiom` for assumptions that establish the formal
setting, and `definition` for new mathematical objects, properties, and
relations. Within each section, axiom through exercise share one numbered
sequence. Problem uses a separate section-scoped sequence. Solution and remark
are unnumbered; proof is the standard `amsthm` environment. Use `ax` as the
label type for numbered axioms.

For formalized results, preserve the environment kind in the Lean docstring
under [declaration documentation](formalization.md#declaration-documentation).
A printed axiom must use explicit assumptions or a checked result, never a new
unchecked Lean `axiom`.

### Labels and references

New labels use `<course-prefix>:<type>:<descriptive-name>`. Use the owning
book's `label_prefix` from `config/books.yml`; do not copy a repository-wide prefix list
into documentation. The supported label syntax and structural policy are defined
in [the architecture guide](ARCHITECTURE.md#labels).
Preserve existing labels. Only replace a duplicate or broken label and update every
reference. Put a numbered environment's `\label` on the same source line as its
`\begin{...}` declaration so that the environment and its repository-global
identifier remain visibly paired.

### Bibliographies and source notes

Each book uses BibLaTeX with the Biber backend. Its `references.bib` file is the
authoritative bibliography source. `sorting=none` lists entries in citation order.
The generated backmatter uses `\nocite{*}` to include uncited entries too.
Use prose or a footnote when no source-note environment is defined.

## Mathematical writing

### Paired mathematical exposition and Lean code

For new or mathematically revised theorems selected for formalization, present
mathematical explanation together with the corresponding Lean code:

- Keep the statement in its numbered mathematical environment with its label.
  Pair the natural-language statement with the corresponding Lean declaration
  signature, preserving domains, hypotheses, quantifiers, and conclusion.
- Keep the proof in a separate `proof` environment. Organize it into successive
  mathematical reasoning units, each with an explanation followed by the
  corresponding Lean proof fragment. A unit may contain several tactics; do not
  divide the exposition mechanically at every code line.
  Use a separate `lean` environment for each substantive unit, including major
  cases or implication directions; blank lines in one box do not replace pairs.
- Write the explanations so that they form a readable mathematical proof even
  when the code is skipped. Explain constructions, deductions, and necessary
  calculations rather than tactic syntax or implementation details. Expand
  automated reasoning when its mathematical justification matters to the reader.
- Keep fragments in proof order and make their dependence on preceding steps
  clear. A displayed fragment may rely on the declaration context and earlier
  fragments; it need not be a standalone Lean program.

Follow the [authoring policy](formalization.md#authoring-policy) for applicability
and the [displayed-code policy](formalization.md#displayed-code-correspondence)
for source correspondence and review. The LaTeX interface is described
[below](#paired-mathematical-prose-and-lean-code).

### Logical introductions

Prefer introductory words that reflect their logical role:

- Prefer `Let` to define a new object or notation, or to choose a witness whose
  existence has already been established. The imperative `Define ...` is also
  natural when explicitly introducing an object, function, or notation. For
  data or a structure supplied by the current hypothesis, `Suppose` is usually
  clearer.
- Prefer `Suppose` to introduce hypotheses and given data in definitions,
  statements, and proofs. It may also restrict attention to a case
  whose complement makes the desired conclusion immediate.
- `Assume` is particularly useful for a temporary assumption, especially in a
  proof by contradiction. Make its temporary role clear when the surrounding
  argument does not already do so.
- Prefer `If` for conditional statements and case distinctions. A direct
  `Suppose` or `Assume` often reads more naturally when opening a proof step.

Keep the distinction when deriving a contradiction. A contradiction obtained
after `Suppose $x \in S$` establishes the conditional conclusion $x \notin S$;
if nonemptiness of $S$ has already been established and the argument
needs an actual element to reach a contradiction, write `Let $x \in S$`.
Likewise, when proving uniqueness, choose one established witness with `Let`,
but introduce an arbitrary competing candidate conditionally with `Suppose`.

### Arbitrary variables

When a proof fixes an element, proves a pointwise claim, and then changes to a
set-level or universally quantified conclusion, an explicit discharge can make
the scope clear:

```tex
Suppose $x \in A$.
% Derive P(x).
Since $x \in A$ was arbitrary,
\[
  \forall x \in A, P(x).
\]
```

These are editorial preferences, not mechanically checked correctness rules.
Prefer an introduction that states the variable's domain explicitly rather than
merely saying it `is arbitrary`. When using `was arbitrary` at discharge,
include the domain rather than writing only `Since $x$ was arbitrary`. The
discharge may be omitted when the scope and conclusion are already clear. In
particular, it is usually unnecessary when the proof obligation or preceding
statement binds the variable with `\forall`, when a structural label such as
`Surjectivity`, `Reflexivity`, `($\subseteq$)`, or `($\supseteq$)` makes
the pointwise obligation explicit, or when the variable is an existential
witness or remains local.

An arbitrary-element argument is valid even when its domain is empty, but it
does not prove that the domain is nonempty. Establish nonemptiness separately
before choosing an element or taking a minimum or maximum.

### Definitions and equalities

Prefer `\coloneqq` when an explicit formula introduces new notation or a new
object, including pointwise definitions of functions and sequences and notation
introduced with `where` or `say`. The ordinary equals sign remains appropriate
for asserted equalities, calculations, equations, and the selection of a
particular value. Thus write `Define $f$ by
$f(x) \coloneqq x^{2}$.` and `where $e_{1} \coloneqq (1,0,\dots,0)$`, but
write `Let $\varepsilon = 1$.` when choosing a value and retain `=` in a
condition such as `x=y`.

### Terminology and emphasis

Prefer `\textbf{...}` for a term at the point where it is defined and
`\emph{...}` for ordinary rhetorical emphasis and conventional proof
qualifiers. If without loss of generality is abbreviated, prefer `\emph{WLOG}`;
spelling out the phrase is equally acceptable.

### Proof organization

Organize proofs around mathematical deductions, with enough prose to connect
each step to its purpose. For formalized results, use the paired format above.
Bold labels such as `Injectivity`, `Surjectivity`, `Base case`, and `Inductive
step` are optional aids for repeated obligations. Displayed implication chains
in an `array` with `\Downarrow` are also optional within an explanation. These
devices supplement the explanation and do not replace the required
explanation/code pairing.

## LaTeX source conventions

### Command ownership

Shared commands are defined in `common/styles/math.sty`; book-specific
additions belong in the owning book's `overrides/style.sty`. Check those files
before introducing or documenting a command.

### Paired mathematical prose and Lean code

Write mathematical prose as ordinary LaTeX immediately before the shared `lean`
environment. The environment takes no arguments and contains only literal Lean
code, printed in a monospaced, bordered box. Do not nest a `verbatim` environment
inside it.

This layout example uses a hypothetical topic file
`lean/Textbooks/LinearAlgebra/VectorSpaces/Equality.lean`:

```lean
namespace LinearAlgebra.VectorSpaces

universe u

/-- Lemma: equality is symmetric. -/
theorem symmetry_of_eq {α : Type u} {x y : α} (h : x = y) : y = x := by
  exact h.symm

end LinearAlgebra.VectorSpaces
```

The corresponding section source contains the signature and proof body;
`u` is the universe declared in the module above:

```tex
\begin{lemma}\label{la:lem:symmetry-of-eq}
  Suppose $x$ and $y$ are elements of the same type and $x=y$.
  Then $y=x$.
  \begin{lean}
theorem symmetry_of_eq {α : Type u} {x y : α} (h : x = y) : y = x
  \end{lean}
\end{lemma}

\begin{proof}
  Symmetry of equality reverses the given equality.
  \begin{lean}
  exact h.symm
  \end{lean}
\end{proof}
```

For an actual textbook result, add `Equality` to the chapter's `modules.yml`
under `modules` (see [source layout](formalization.md#source-layout)), run
`ashaiy generated generate --book linear-algebra`, and check Lean before writing the exposition
in `books/linear-algebra/chapters/vector-spaces/linear-combinations.tex`.
Then add the matching entry to that chapter's `proofs.yml`:

```yaml
proofs:
  - id: la:lem:symmetry-of-eq
    declaration: LinearAlgebra.VectorSpaces.symmetry_of_eq
```

Keep existing entries and run the applicable
[validation checks](CONTRIBUTING.md#validation-by-change-category).

Keep the closing `\end{lean}` on its own line. The formatter preserves
relative Lean indentation, but aligns the block to the surrounding environment
and condenses consecutive blank lines. Format the preceding prose using normal
LaTeX indentation, independently of the code. Use the
[Lean readability conventions](formalization.md#lean-readability) inside each
block and the [paired exposition format](#paired-mathematical-exposition-and-lean-code)
to divide the proof into explanation/code pairs.

Prose and display math follow normal LaTeX page flow independently of the code.
Code boxes can split across pages, requiring room for six lines before splitting
so short boxes normally stay together.
Long boxes continue with side borders and an open edge at the page break. Keep
explanations short and organize arguments into mathematical reasoning units with
their corresponding code; do not reduce font size or omit reasoning to fit a
page. Review page breaks for detached explanations, overflow, and awkward
transitions.

### Fonts and Unicode

Store text sources as UTF-8 with LF line endings. Choose characters for their
mathematical or linguistic meaning; font coverage must not determine the
statement or the checked Lean source. Do not introduce invisible format
characters, nonbreaking spaces, or look-alike characters merely to adjust
layout. Use LaTeX spacing commands in prose. When a language or a checked
identifier needs combining characters, preserve them deliberately rather than
applying a blanket Unicode normalization or ASCII conversion.

| Context | Source convention |
|---|---|
| LaTeX mathematical prose | Use math mode and the existing macros, such as `$\N$`, `$\N^{+}$`, and `$\bigcup_{i} E_{i}$`; do not paste a bare mathematical Unicode glyph into ordinary text as a font workaround. |
| Ordinary prose and PDF bookmark strings | Unicode appropriate to the language and supported by the selected text font is allowed; preserve existing `\texorpdfstring` alternatives. |
| Checked Lean and displayed Lean | Keep the actual identifiers and notation, including `ℕ`, `ℕ+`, `⋃`, and `⋂`. Displayed fragments must follow the [checked-source correspondence policy](formalization.md#displayed-code-correspondence). |
| Typesetting fixtures | Literal glyph inventories are allowed and must be identified as rendering specimens, not checked mathematical proofs. |

`common/styles/code.sty` owns code fonts and fallback for all books. Use fonts
from the supported TeX Live environment; do not duplicate font setup in books,
substitute look-alike symbols, or suppress missing-character diagnostics.
Font fallback can change symbol metrics, so visual review remains necessary.

For new notation, extend
[`tests/fixtures/lean-glyphs.tex`](../tests/fixtures/lean-glyphs.tex). The
[`lean-fonts.tex`](../tests/fixtures/lean-fonts.tex) specimen exercises the real
code environment's font shapes and syntax styling. Run:

```sh
python3 -m unittest discover -s tests -p 'test_code_fonts.py' -v
```

Review `build/font-check/lean-fonts.pdf` and affected textbook pages for symbols,
baselines, wrapping, and clipping. The test checks compilation and strict logs;
it runs under `ashaiy test` when LaTeX tools are available. A skip does not validate
fonts. Missing-character diagnostics always fail log checks; strict mode also
rejects overfull boxes. Shared font changes require the
[complete validation suites](CONTRIBUTING.md#validation-by-change-category),
including `ashaiy test` and `ashaiy check all --strict`.

### Braces in command arguments and scripts

Prefer braces around every mandatory command argument and every subscript or
superscript argument, including single characters. For example, write
`\frac{1}{n}`, `N_{r}(p)`, `\mathcal{G}_{2}(b)`, and `x^{2}`.
