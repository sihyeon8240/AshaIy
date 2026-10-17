# Site metadata

## Registry fields

[`config/books.yml`](../config/books.yml) owns book metadata and automation flags.
The [editor schema](../config/schemas/books.schema.json) describes field shapes;
`scripts/book_manifest.py` enforces semantic constraints and uniqueness.

| Fields | Requirement and meaning |
|---|---|
| `slug`, `title` | Required stable lowercase hyphenated identifier and nonempty single-line title. Slugs are unique. |
| `version` | Required semantic version, such as `0.1.0` or `0.2.0-rc.1`. |
| `status`, `order` | Required status below and integer display order; equal orders sort by slug. |
| `author` | Required nonempty single-line name, directly or through `defaults`. |
| `build`, `check`, `release`, `site` | Required booleans, directly or through `defaults`; select bulk builds, full checks, releases, and site publication. |
| `short_title` | Optional nonempty single-line title for site cards; defaults to `title`. |
| `label_prefix` | Optional unique lowercase alphanumeric prefix beginning with a letter; defaults to the slug's initials. Set it explicitly to keep labels stable. |
| `lean_module` | Optional unique UpperCamelCase name; required before adding Lean sources. |

The root uses `schema_version: 1` and a `books` list. `defaults` may contain only
`author` and the four boolean flags; each book's explicit values override them.
Unknown fields are errors. After metadata edits, run `ashaiy config generate`,
`ashaiy config check`, and `ashaiy contents generate --book <slug>`; refresh site pages when
needed as described below.

`ashaiy book build --book <slug>` builds a registered book regardless of its `build`
flag. Release preparation requires `build: true` and enables `release: true`.
A reviewed transition to `release: true` publishes the current version;
subsequent version increases publish new releases after main CI succeeds. See [Releases](developer-workflow.md#releases).

Statuses describe publication state:

- `draft`: actively being written and not an official distribution
- `review`: planned material is largely present and under review
- `published`: an official versioned PDF is public
- `archived`: no longer actively maintained

A published book may continue to evolve. Status is descriptive; automation
participation is controlled separately by the boolean flags.

## Generated site pages

`ashaiy site generate` selects normalized `site: true` books and writes that metadata into
ignored `site/books/<slug>.md` page front matter for a local or CI build. Pass
`--book <slug>` to limit generation to one site-enabled book.

`ashaiy site check` compares existing pages with the expected rendering without
writing files. It rejects stale, missing, and orphaned pages. Run `ashaiy site generate`
first in a clean checkout, where the ignored pages are absent. With
`--book <slug>`, check mode validates only that book's page.

Publishing a book on the site requires `build: true` and `site: true` in
`config/books.yml`. Manifest validation rejects `site: true` with `build: false`.
After changing the manifest, follow [Refreshing local pages](#refreshing-local-pages)
and the applicable [validation requirements](CONTRIBUTING.md#validation-by-change-category).
Use `ashaiy check source` to validate fresh rendering in a temporary directory
when local site pages are not needed.

The build workflow downloads PDF artifacts to update the `generated-pdfs`
branch. Pages checks out that complete snapshot and stages only `site: true`
books as `pdf/<slug>.pdf`; PDFs for registered books with `site: false` are
ignored. The snapshot README comes from `.github/generated-pdfs-README.md`.

The shared document layout and header/footer includes live under
`site/_layouts/` and `site/_includes/`. Site identity lives in `site/_config.yml`.
Shared component and accessibility rules live in `site/assets/common.css`;
`index.css` and `book.css` own page-specific presentation and responsive behavior.

The index reads generated book pages through `site.pages`, sorts them by
manifest order, and displays short titles and status labels. Detail pages and
accessible link names use the full title. The book layout reads the same front
matter, including Lean coverage generated from the proof index.

Lean coverage is the number of LaTeX results linked to a Lean declaration through
the proof index divided by the book's LaTeX theorem, lemma, proposition, and
corollary count, expressed as a percentage rounded to one decimal place.
Each result counts once regardless of the number of registered labels. Comments
and literal code samples are excluded; unlabeled results remain in the denominator.
Lean-only results do not belong in the proof index and do not contribute to coverage.
Coverage cannot exceed 100%. When the LaTeX count is zero, both the linked count
and the percentage are zero.

The generator supplies status labels and uses the full title when `short_title`
is absent. Official-release links open the repository's GitHub Releases page.
GitHub links use the repository URL in `site/_config.yml`.
See [Repository architecture](ARCHITECTURE.md#metadata-and-automation) for
metadata ownership and automation policy.

## PDF snapshot URLs

The generator records the source checkout's commit as `snapshot_revision`.
Pages builds check out the source commit recorded by the PDF snapshot, so this
identifies the published snapshot. The shared PDF URL include uses the same
revision query for cards, previews, direct reading, fallback links, and downloads.
Rebuilding the same commit preserves the URL; a different commit changes it.
Source exports without Git metadata use unversioned URLs. Uncommitted local
PDF changes do not change the revision; disable browser caching when previewing
such changes locally.

## Refreshing local pages

After changing `config/books.yml`, theorem sources, proof-index entries, or the source
checkout's commit, run
`ashaiy site generate` and then `ashaiy site check` before a local Jekyll build. This refreshes
publication status, Lean coverage, and the snapshot revision. Keep `site/books/`
untracked and regenerate stale pages. CI generates fresh pages for each site
build. `ashaiy check source` checks rendering in a temporary directory; use
`ashaiy site check` to validate local generated pages.

### Local preview

Use the development image with Jekyll, Chromium, and ChromeDriver installed.
From the repository root:

```sh
ashaiy book build
ashaiy site build
ashaiy site serve
```

`build` regenerates site pages, renders Jekyll into `build/site-preview/`, and
copies site-enabled books from `build/<slug>/book.pdf`. Build changed textbooks
first; missing or empty PDFs cause an error with the required build commands.
`serve` builds first, then serves the result at `http://localhost:4000` until
Ctrl+C. Override the port with `ashaiy site serve --port <port>`. Rerun after changes; there is
no automatic rebuild. Generated pages and output remain ignored, and Jekyll's
disk cache is disabled.

In VS Code, use **Tasks: Run Task** and select `ashaiy site build`,
`ashaiy site serve`, or `ashaiy site test`. The development container forwards port
4000 and labels it in the Ports panel; open that address in a browser or use
VS Code's **Simple Browser: Show** command. For another port, forward it in the
Ports panel. Stop the background preview with **Tasks: Terminate Task**.

## Rendered validation

```sh
ashaiy site test
```

This runs site generation, rendered HTML, and responsive Chromium tests with temporary fixtures, including special-character titles, relative
links, release visibility, PDF URLs, and mobile/tablet/desktop bounds. It requires
Jekyll, Chromium, and ChromeDriver so missing tools cannot silently skip these
checks. It does not require local PDFs or a running preview server. Under
`ashaiy test`, these tool-dependent checks report skips when tools are unavailable.
Review the actual local site and its PDF links manually as well.

Local preview uses the installed Jekyll; deployment uses GitHub's Jekyll build
action. Deployment permissions and remote PDF snapshot validation remain CI
responsibilities. After changing the development image pin, recreate the
container to use that image's tools. Packages installed manually in a running
container are lost when it is recreated.
