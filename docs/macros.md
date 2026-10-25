# LaTeX macro declarations

Declare mathematical commands in YAML so LaTeX generation and formatting use
the same definitions and argument signatures.

| Scope | Manifest | Generated package |
|---|---|---|
| Shared | [`common/styles/macros.yml`](../common/styles/macros.yml) | `common/styles/generated-macros.sty` |
| Book-local | `books/<slug>/styles/macros.yml` | `books/<slug>/styles/generated-macros.sty` |

Edit manifests and commit their generated packages together. Create a book-local
manifest only when needed, and remove its package when removing the manifest.
See [architecture](ARCHITECTURE.md#macro-declarations) for package loading and
shared-style ownership.

## Naming and shared notation

Use ASCII-letter names beginning with an uppercase letter. Choose familiar
symbol names for general-purpose delimiters and mathematical names for
structured notation. Keep each command's argument count and role fixed;
reuse existing commands rather than adding aliases or spelling variants.

Share notation when books agree on its meaning, signature, and typesetting.
Keep subject-specific notation in its owning book. Names must be unique across
shared declarations and a book's local declarations, and must not collide with
existing TeX or package commands. Consult the manifests for available commands.

## Manifest format

For example:

```yaml
schema_version: 1
macros:
  Span:
    kind: command
    arguments:
      - {kind: mandatory, mode: math}
    body: '\operatorname{span}\Paren*{#1}'
  Rank:
    kind: operator
    text: rank
```

Use single-quoted YAML strings to preserve TeX backslashes. Arguments are listed
in order and referenced as `#1`, `#2`, and so on in the body.

| Kind | Purpose | Main fields |
|---|---|---|
| `command` | General mathematical command | `arguments`, `body` |
| `operator` | Named operator | `text`; optional `limits` |
| `paired_delimiter` | Delimiters around one math argument | `left`, `right` |
| `paired_delimiter_x` | Delimiters with structured arguments | `arguments`, `left`, `right`, `body`; optional `after` |

Argument modes control formatting: `math` normalizes mathematics, `text` preserves
text while recognizing embedded math, and `opaque` preserves all contents.
Commands may have one leading optional argument with a `default`. Their `context`
defaults to `math`; use `text` or `any` when needed. Set `script_atom: true` only
when the whole call can safely be grouped as one math field in a script.

Paired delimiters use the default size unless called with `*` for automatic
sizing or an optional explicit size. Do not combine these two size options.

See the [manifest schema](../config/schemas/macros.schema.json) for supported
fields and constraints, and the existing manifests for working declarations.

## Generation and formatting

```sh
ashaiy macros generate
ashaiy macros check
ashaiy format tex
```

Generate packages after editing manifests and before formatting TeX. Generation
validates all registered books; add `--book <slug>` to select shared declarations
and one book. Check mode verifies packages without writing.

Formatting uses shared declarations plus those of the book owning the source.
Stale packages must be regenerated first. See the
[writing guide](writing-guide.md#braces-in-command-arguments-and-scripts) for brace
normalization and source preservation, and the
[validation matrix](CONTRIBUTING.md#validation-by-change-category) for required checks.
