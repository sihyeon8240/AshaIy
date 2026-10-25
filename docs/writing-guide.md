# Textbook writing guide

This guide owns LaTeX authoring and mathematical exposition. Structural rules
and paired exposition for new or mathematically revised formalized theorems are
required; other prose and proof-layout conventions are recommendations. Follow
the [Lean-first policy](formalization.md#authoring-policy) before writing formalized results.

## Book structure and manifests

### Creating and registering a book

Create and register a book from the repository root with:

```sh
ashaiy book new --slug <slug> --title "<title>"
```

The script copies `common/templates/`, creates the first chapter and section,
and registers the book in `config/books.yml`. The lower-level `books.py add` command
only registers an existing directory and inherits registry defaults. A new scaffold
explicitly disables `release` and `site`, regardless of those defaults, until its
publication settings are reviewed. After creation, run:

```sh
ashaiy config generate
ashaiy config check
```

Review and commit the new sources, `config/books.yml`, and all synchronized
consumers together. Complete the applicable
[validation checks](CONTRIBUTING.md#validation-by-change-category) before review.

Complete the scaffold's `formalization.md` before adding formalized results,
following [book-owned prerequisite boundaries](formalization.md#book-owned-prerequisite-boundaries).
Its [template](../common/templates/formalization.md) supplies no mathematical prerequisites.

### Generated assembly and section files

Write each logical section's body in one `section-name.tex`, without `\chapter`,
`\section`, or package loads. Generate `book.tex` and chapter/appendix `index.tex`
from manifests; do not edit assembly by hand.

Keep slugs stable when changing titles or reading order. Set a stable
UpperCamelCase `lean_namespace` before adding a chapter or appendix's Lean
sources. See [assembly ownership](ARCHITECTURE.md#book-assembly-and-file-responsibilities)
and [naming](ARCHITECTURE.md#naming-conventions).

### Contents manifests and metadata

Edit the `chapters` and optional `appendices` lists in `chapters.yml` and
their `sections.yml` files, then run `ashaiy contents generate --book <slug>`.
Titles may contain LaTeX, including `\texorpdfstring` for PDF-safe alternatives.

The `sections` and `all` scopes initialize missing `proofs.yml` files from
[the template](../common/templates/proofs.yml), preserving existing entries.
Maintain those entries by hand; check mode reports missing files without writing.

Use meaningful ASCII slugs: preserve mathematical identifiers
and exponents (for example, `functions-of-class-l2` and `the-number-e`) instead
of deriving a lossy slug from rendered title text.

For `config/books.yml` edits, follow the
[registry synchronization steps](site-metadata.md#registry-fields), including
configuration and assembly generation. Optional frontmatter overrides follow
[architecture](ARCHITECTURE.md#book-assembly-and-file-responsibilities).

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
ashaiy contents check --book <slug>
```

Use a chapter slug not already registered in that book. For a section in an
existing chapter, add only its `sections.yml` entry and source file, then use
the same commands. Complete the [required formatting, source checks, and book build](CONTRIBUTING.md#validation-by-change-category),
then commit manifests, sources, assembly, and the initialized proof index together.

### Authoring and style files

Use [macro manifests](macros.md) for mathematical commands and shared styles
for package loading and typography.

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

- Use `Let` or `Define` for new objects and notation; use `Let` to choose a
  witness whose existence is established.
- Use `Suppose` for hypotheses, given data, and cases whose complement is immediate.
- Use `Assume` for temporary assumptions, especially in contradiction proofs;
  make that temporary role clear.
- Use `If` for conditional statements and case distinctions. `Suppose` or
  `Assume` often reads more naturally when opening a proof step.

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

State the domain when introducing or discharging an arbitrary variable. These
are editorial preferences, not mechanically checked rules. Omit the discharge
when scope is clear: a preceding `\forall` or a label such as `Surjectivity` or
`($\subseteq$)` may already identify the obligation. Existential witnesses
and variables that remain local need no arbitrary-variable discharge.

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

Shared mathematical commands are declared in `common/styles/macros.yml`; book-specific
additions belong in `books/<slug>/styles/macros.yml`. Check those files before
introducing or documenting a command, then run `ashaiy macros generate`.
See [LaTeX macros](macros.md) for argument signatures and generated packages.

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

For an actual result, register and check the topic under
[source layout](formalization.md#source-layout) before writing its exposition.
Then [link the label to the checked declaration](formalization.md#linking-a-verified-proof)
in the chapter's `proofs.yml` and run the applicable
[validation](CONTRIBUTING.md#validation-by-change-category).

Keep the closing `\end{lean}` on its own line. The formatter preserves
relative Lean indentation, but aligns the block to the surrounding environment
and condenses consecutive blank lines. Blocks containing multiline string
literals are preserved as a whole because their whitespace is part of the value.
Format prose with normal LaTeX indentation, independently of the code. Use the
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
python3 -m unittest discover -t . -s tests/latex -p 'test_code_fonts.py' -v
```

Review `build/font-check/lean-fonts.pdf` and affected pages for symbols, baselines,
wrapping, and clipping. The test checks compilation and strict logs; see
[tool-dependent tests](../tests/README.md) for skips. Missing-character diagnostics
always fail log checks; strict mode also rejects overfull boxes. Shared font
changes require the [complete validation suites](CONTRIBUTING.md#validation-by-change-category).

### Braces in command arguments and scripts

Prefer braces around every mandatory command argument and every subscript or
superscript argument, including single characters. For example, write
`\frac{1}{n}`, `N_{r}(p)`, `\mathcal{G}_{2}(b)`, and `x^{2}`.

VS Code formatting on save and `ashaiy format tex` add these braces to math
scripts and registered standard command arguments, such as `\int_0^1`,
`\frac12`, `\sqrt x`, and `\mathcal G`. Optional arguments such as the index in
`\sqrt[3]{x}` retain their square brackets. The supported command names and
argument signatures live in
[`command_specs.py`](../scripts/latex/command_specs.py) and the macro manifests.

The normalizer distinguishes math from text and preserves comments, literal
code, macro definitions, and braced arguments of unregistered commands.
Registered user macros follow the [manifest contract](macros.md); the formatter
does not expand unregistered macros or infer their argument conventions.
