#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "usage: $0 FILE" >&2
  exit 2
fi

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
eof_formatter="$repository_root/scripts/normalize-eof.sh"
format_settings="$repository_root/config/latexindent.yaml"
file="$1"
cruft_directory="$(mktemp -d)"
trap 'rm -rf "$cruft_directory"' EXIT

# Preserve relative Lean indentation inside code-only environments.
normalize_lean_indentation() {
  perl -0777 -pe '
    s{^([\t ]*)(\\begin\{lean\}[\t ]*(?:%[^\n]*)?\n)(.*?)^[\t ]*(\\end\{lean\}[\t ]*(?:%[^\n]*)?$)}
     {
       my ($indent, $opening, $body, $closing) = ($1, $2, $3, $4);
       my $common;
       while ($body =~ /^([\t ]*)\S/gm) {
         my $prefix = $1;
         if (!defined $common) { $common = $prefix; }
         else {
           chop $common while length($common) && index($prefix, $common) != 0;
         }
       }
       if (defined $common) {
         $body =~ s/^\Q$common\E(?=[^\n]*\S)/$indent . "  "/gme;
       }
       $indent . $opening . $body . $indent . $closing;
     }gmse;
  ' "$1" >"$cruft_directory/lean-normalized.tex"
}

wrapped_file="$cruft_directory/wrapped.${file##*.}"
formatted_file="$cruft_directory/formatted.${file##*.}"
latexindent \
  --modifylinebreaks \
  --local="$format_settings" \
  --cruft="$cruft_directory" \
  "$file" >"$wrapped_file"

# latexindent 4.0.2 adds extra indentation to short wrapped sentences.
# An indentation-only pass keeps the final result at the configured depth.
latexindent \
  --local="$format_settings" \
  --cruft="$cruft_directory" \
  "$wrapped_file" >"$formatted_file"
normalize_lean_indentation "$formatted_file"
"$eof_formatter" --collapse-blank-lines "$cruft_directory/lean-normalized.tex"
cat "$cruft_directory/lean-normalized.tex"
