"""File roles shared by CI, source selection, and conservative PDF planning."""

IMAGE_PIPELINE = {
    "scripts/repository/config/json_config.py",
    "config/validation-patterns.json",
    "scripts/repository/config/validation_patterns.py",
    "scripts/repository/config/validation_sync.py",
    "scripts/toolchain/images/check_image_tag.sh",
    "scripts/ci/ci_changes.py",
    "scripts/repository/path_policy.py",
    "scripts/toolchain/images/image_registry.py",
    ".github/actions/load-toolchain/action.yml",
    ".github/actions/run-toolchain/action.yml",
    "scripts/toolchain/images/image_pr.py",
    ".github/workflows/pin-pr-image.yml",
    "scripts/toolchain/images/image_policy.py",
    "scripts/repository/config/repository_config.py",
    "scripts/toolchain/images/image_candidate.py",
    "scripts/ci/github_artifacts.py",
    ".github/workflows/build.yml",
    ".github/workflows/build-image.yml",
    ".github/workflows/build-toolchain.yml",
    ".github/workflows/prepare-image.yml",
}

SITE_FILES = {
    "scripts/site/check_site_output.py",
    ".github/workflows/pages.yml",
    "scripts/site/site_pages.py",
    "scripts/lean/lean_coverage.py",
    "scripts/site/stage_site_pdfs.py",
}

SNAPSHOT_FILES = {
    ".github/generated-pdfs-README.md",
    "scripts/release/publish_snapshot.sh",
    "scripts/release/snapshot_state.py",
}

CI_ONLY_FILES = {
    "scripts/toolchain/images/image_pr.py",
    "scripts/ci/ci_check_scope.py",
    "scripts/ci/ci_changes.py",
    "scripts/ci/verified_build.py",
    "scripts/ci/github_artifacts.py",
    "scripts/toolchain/images/image_candidate.py",
    "scripts/site/pages_current.sh",
    "scripts/release/release_package.py",
    "scripts/release/release_retry.py",
    "scripts/release/releases.py",
    "scripts/release/release_plan.sh",
    "scripts/release/publish_release.sh",
    "scripts/release/package_book.sh",
    "scripts/toolchain/images/check_image_reference.py",
    "scripts/toolchain/images/check_image_tag.sh",
    "scripts/repository/config/config_sync.py",
    "scripts/repository/config/export_config.sh",
    "scripts/release/upload_release_assets.sh",
    "scripts/repository/config/repository_config.py",
    "scripts/release/snapshot_base.sh",
}

BUILD_INFRA = {
    "config/validation-patterns.json",
    "scripts/repository/config/validation_patterns.py",
    "scripts/ashaiy",
    "scripts/cli/repository_cli.py",
    "scripts/cli/repository_commands.py",
    "scripts/cli/repository_tasks.py",
    "config/latexmkrc",
    "scripts/latex/build_book.sh",
    "scripts/latex/build_support.sh",
    "scripts/latex/build_all.py",
    "scripts/latex/check_log.py",
    "scripts/books/books.py",
    "scripts/books/book_manifest.py",
    "config/container-image.txt",
    "common/templates/book.tex",
    "scripts/books/contents_manifest.py",
    "scripts/books/contents_generation.py",
}

SAFE_PATHS = {
    ".github/dependabot.yml",
    ".devcontainer/devcontainer.json",
    "config/container-image.txt",
}

SCAFFOLD_FILES = {
    "common/templates/chapter.tex",
    "common/templates/chapters.yml",
    "common/templates/cover.tex",
    "common/templates/formalization-versions.tex",
    "common/templates/preface.tex",
    "common/templates/proofs.yml",
    "common/templates/references.bib",
    "common/templates/sections.yml",
    "common/templates/section.tex",
}
