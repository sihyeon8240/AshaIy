# Site metadata

Use this guide for registry fields, generated book pages, local previews, and site
validation. The [maintainer guide](maintainer-guide.md#site-publication-checklist)
owns remote publication and recovery.

## Registry fields

[`config/books.yml`](../config/books.yml) owns book metadata and automation flags.
The [editor schema](../config/schemas/books.schema.json) describes field shapes;
`scripts/book_manifest.py` enforces semantic constraints and uniqueness.

| Fields | Requirement and meaning |
|---|---|
| `slug`, `title` | Required stable lowercase hyphenated identifier and nonempty single-line title. Slugs are unique. |
| `version` | Required directly or through `defaults`; semantic version, such as `0.1.0` or `0.2.0-rc.1`. |
| `status` | Required directly or through `defaults`; one of the statuses below. |
| `order` | Required integer display order; equal orders sort by slug. |
| `author` | Required nonempty single-line name, directly or through `defaults`. |
| `build`, `check`, `release`, `site` | Required booleans, directly or through `defaults`; select bulk builds, full checks, releases, and site publication. |
| `label_prefix` | Optional unique lowercase alphanumeric prefix beginning with a letter; defaults to the slug's initials. Set it explicitly to keep labels stable. |
| `lean_module` | Optional unique UpperCamelCase name; required before adding Lean sources. |

The root uses `schema_version: 1` and a `books` list. `defaults` may contain only
`author`, `version`, `status`, and the four boolean flags; each book's explicit values override them.
Unknown fields are errors. After metadata edits, run `ashaiy config generate`,
`ashaiy config check`, and `ashaiy contents generate --book <slug>`; refresh site pages when
needed as described below.

Registry `title` and `author` are plain text. LaTeX generation escapes their
special characters; site generation renders them as text. Chapter and section
titles are LaTeX: balance braces and write `\%` for a literal percent sign.

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

`ashaiy site generate` writes ignored `site/books/<slug>.md` pages for
`site: true` books. `ashaiy site check` compares them without writing and rejects
missing, stale, or orphaned pages. Generate first in a clean checkout. Both accept
`--book <slug>` for one site-enabled book.

Site publication requires `build: true` and `site: true`; manifest validation
rejects `site: true` with `build: false`. Enabling `site` builds the book even
if PDF sources are unchanged; disabling it removes its snapshot PDF without rebuilding.
After edits, follow [Refreshing local pages](#refreshing-local-pages) and the
[validation matrix](CONTRIBUTING.md#validation-by-change-category).

The build workflow downloads PDF artifacts to update the `generated-pdfs`
branch. Pages checks out that complete snapshot and stages only `site: true`
books as `pdf/<slug>.pdf`; PDFs for registered books with `site: false` are
ignored. The snapshot README comes from `.github/generated-pdfs-README.md`.

The shared document layout and header/footer includes live under
`site/_layouts/` and `site/_includes/`. Site identity lives in `site/_config.yml`.
Shared component and accessibility rules live in `site/assets/common.css`;
`index.css` and `book.css` own page-specific presentation and responsive behavior.

The index reads generated book pages through `site.pages`, sorts them by
manifest order, and displays titles and status labels. Cards, detail pages, and
accessible link names all use `title`. The book layout reads the same front
matter, including Lean coverage generated from the proof index.

Lean coverage is the number of LaTeX results linked to a Lean declaration through
the proof index divided by the book's LaTeX theorem, lemma, proposition, and
corollary count, expressed as a percentage rounded to one decimal place.
Each result counts once regardless of the number of registered labels. Comments
and literal code samples are excluded; unlabeled results remain in the denominator.
Lean-only results do not belong in the proof index and do not contribute to coverage.
Coverage cannot exceed 100%. When the LaTeX count is zero, both the linked count
and the percentage are zero.

Release links open GitHub Releases. Site links use the repository URL from
`site/_config.yml`. See [architecture](ARCHITECTURE.md#metadata-and-automation)
for metadata ownership.

## PDF snapshot URLs

Pages sets `SITE_SNAPSHOT_SHA` to the immutable PDF snapshot commit. The generator
records it as `snapshot_revision`, and the shared PDF URL include uses that query
value for cards, previews, direct reading, fallback links, and downloads. Rebuilding
the same source with different PDF bytes creates a new snapshot commit and URL.
The separate `source_revision` field records the source checkout that produced
the snapshot; Jekyll's build revision uses that source commit as well.

Local generation falls back to the source checkout's commit when no deployment
snapshot is supplied. Source exports without Git metadata use unversioned URLs.
Uncommitted local PDF changes do not change the revision; disable browser caching
when previewing such changes locally.

## Refreshing local pages

After changing metadata, theorem sources, proof indexes, or the checkout commit,
run `ashaiy site generate` and `ashaiy site check` before a local Jekyll build.
This refreshes status, coverage, and snapshot revision. Keep pages untracked.
CI generates them afresh; `ashaiy check source` validates rendering in a temporary
directory, independently of local pages.

### Local preview

Use the development image with Jekyll, Chromium, and Playwright installed.
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
Jekyll, Chromium, and Playwright so missing tools cannot silently skip these
checks. It does not require local PDFs or a running preview server. Under
`ashaiy test`, these tool-dependent checks report skips when tools are unavailable.
Review the actual local site and its PDF links manually as well.

Local preview uses the installed Jekyll; deployment uses GitHub's Jekyll build
action. Before uploading the actual deployment artifact, CI validates local HTML,
CSS resource, image, and PDF links, HTML anchors, PDF headers, and PDF checksums
against the downloaded snapshot. These checks use Pages' configured base path.
Rendered fixtures exercise the same checker locally. Deployment permissions and
remote PDF snapshot validation remain CI responsibilities. Recreate the container after changing its image pin.
