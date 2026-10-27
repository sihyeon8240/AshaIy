#!/usr/bin/env bash

prepare_output_tree() {
  local source_directory="$1" output_directory="$2" source_dir relative

  mkdir -p "$output_directory"
  while IFS= read -r -d '' source_dir; do
    relative="${source_dir#"$source_directory"/}"
    mkdir -p "$output_directory/$relative"
  done < <(find "$source_directory" -mindepth 1 -type d -print0)
}

build_document() (
  local repository_root="$1" source_directory="$2" output_directory="$3" document="$4"
  shift 4
  local status pdf build_lock build_environment environment_record epoch changed option
  local shell_escape_options=() rebuild_options=()

  case "${SHELL_ESCAPE:-0}" in
    0) ;;
    1) shell_escape_options=(-shell-escape) ;;
    *)
      echo "error: SHELL_ESCAPE must be 0 or 1" >&2
      exit 2
      ;;
  esac

  prepare_output_tree "$source_directory" "$output_directory"
  output_directory="$(cd "$output_directory" && pwd)"
  exec {build_lock}> "$output_directory/.build.lock"
  flock "$build_lock"
  pdf="$output_directory/${document%.tex}.pdf"
  environment_record="$output_directory/${document%.*}.build-environment.json"
  local effective_shell_escape="${SHELL_ESCAPE:-0}"
  for option in "$@"; do
    case "$option" in
      -shell-escape) effective_shell_escape=1 ;;
      -no-shell-escape) effective_shell_escape=0 ;;
    esac
  done
  if ! build_environment="$(SHELL_ESCAPE="$effective_shell_escape" "${PYTHON:-python3}" \
    "$repository_root/scripts/latex/build_environment.py" "$repository_root" "$output_directory" "$document")"; then
    rm -f -- "$pdf"
    exit 2
  fi
  read -r epoch changed <<< "$build_environment"
  if [[ "$changed" == 1 ]]; then
    rebuild_options=(-g)
  fi
  export SOURCE_DATE_EPOCH="$epoch" FORCE_SOURCE_DATE=1 TZ=UTC LC_ALL=C.UTF-8
  export TEXINPUTS=".:$repository_root/common/styles//:$repository_root/common/templates//:${TEXINPUTS:-}"
  cd "$source_directory"

  # Keep successful output for dependency checks, but never retain a failed build.
  trap 'rm -f -- "$pdf"; exit 130' HUP INT TERM
  if latexmk -r "$repository_root/config/latexmkrc" -lualatex \
    -outdir="$output_directory" "${rebuild_options[@]}" "${shell_escape_options[@]}" "$@" "$document" &&
    mv -- "$output_directory/.${document%.*}.build-environment.json.pending" "$environment_record"; then
    trap - HUP INT TERM
  else
    status=$?
    rm -f -- "$pdf"
    exit "$status"
  fi
)
