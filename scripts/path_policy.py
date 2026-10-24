"""File roles shared by CI, source selection, and conservative PDF planning."""

IMAGE_PIPELINE = {
    "config/validation-patterns.json",
    "scripts/validation_patterns.py",
    "scripts/validation_sync.py",
    "scripts/check_image_tag.sh",
    "scripts/ci_changes.py",
    "scripts/path_policy.py",
    "scripts/image_registry.py",
    ".github/actions/load-toolchain/action.yml",
    ".github/actions/run-toolchain/action.yml",
    "scripts/image_pr.py",
    ".github/workflows/pin-pr-image.yml",
    "scripts/image_policy.py",
    "scripts/repository_config.py",
    "scripts/image_candidate.py",
    "scripts/github_artifacts.py",
    ".github/workflows/build.yml",
    ".github/workflows/build-image.yml",
    ".github/workflows/build-toolchain.yml",
    ".github/workflows/prepare-image.yml",
}

SITE_FILES = {
    "scripts/check_site_output.py",
    ".github/workflows/pages.yml",
    "scripts/generate_site_pages.py",
    "scripts/site_pages.py",
    "scripts/lean_coverage.py",
    "scripts/stage_site_pdfs.py",
}

SNAPSHOT_FILES = {
    ".github/generated-pdfs-README.md",
    "scripts/publish_snapshot.sh",
    "scripts/snapshot_state.py",
}

CI_ONLY_FILES = {
    "scripts/image_pr.py",
    "scripts/ci_check_scope.py",
    "scripts/ci_changes.py",
    "scripts/verified_build.py",
    "scripts/github_artifacts.py",
    "scripts/image_candidate.py",
    "scripts/pages_current.sh",
    "scripts/release_package.py",
    "scripts/release_retry.py",
    "scripts/releases.py",
    "scripts/release_plan.sh",
    "scripts/publish_release.sh",
    "scripts/package_book.sh",
    "scripts/check_image_reference.py",
    "scripts/check_image_tag.sh",
    "scripts/config_sync.py",
    "scripts/export_config.sh",
    "scripts/upload_release_assets.sh",
    "scripts/repository_config.py",
    "scripts/snapshot_base.sh",
}

BUILD_INFRA = {
    "config/validation-patterns.json",
    "scripts/validation_patterns.py",
    "scripts/ashaiy",
    "scripts/repository_cli.py",
    "scripts/repository_commands.py",
    "scripts/repository_tasks.py",
    "config/latexmkrc",
    "scripts/build_book.sh",
    "scripts/build_support.sh",
    "scripts/build_all.sh",
    "scripts/check_log.py",
    "scripts/books.py",
    "scripts/book_manifest.py",
    "config/container-image.txt",
    "common/templates/book.tex",
    "scripts/contents_manifest.py",
    "scripts/generate_contents.py",
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
