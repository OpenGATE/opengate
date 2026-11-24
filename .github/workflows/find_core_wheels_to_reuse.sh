#!/usr/bin/env bash
#
# Decide which opengate_core wheels the CI run needs (OS x Python version),
# and whether they can be reused from a previous master run instead of being
# built again (the build of the 15 wheels takes ~30 min, macOS runners are
# scarce).
#
# Prints to $GITHUB_OUTPUT (or stdout when run locally):
#   matrix=<json>         list of {"os": ..., "python-version": ...}, used by
#                         the build and test jobs
#   reuse_run_id=<id>     master run whose wheels are reused (empty: build)
#
# Matrix:
#   - schedule, workflow_dispatch, tags, label "full-matrix": 3 OS x 5 Python
#   - pull request: 3 OS x (3.10, 3.14)
#   - push to master: Linux and Windows x 5 Python, macOS x (3.10, 3.14)
#     (macOS runners are the bottleneck; the scheduled runs test them all)
#
# Reuse (pull requests and pushes to master, not tags, schedule or manual
# runs): the wheels of a master run (push or schedule) are reused if the
# opengate_core sources (core/, VERSION, the build action and main.yml) are
# identical in that run and in the commit tested here, and if all the wheels
# of the matrix are among its artifacts.
#
# Environment:
#   EVENT_NAME  github.event_name
#   REF         github.ref (refs/tags/... for a tag)
#   LABELS      labels of the pull request, comma separated: "build-core"
#               forces the build, "full-matrix" all Python versions
#   HEAD        commit to compare (default: HEAD, i.e. the merge commit
#               checked out for a pull request, or the pushed commit)
#   GH_TOKEN    token for the GitHub API (gh)

set -uo pipefail
export LC_ALL=C  # same order for sort and comm

REPO="${GITHUB_REPOSITORY:-OpenGATE/opengate}"
EVENT_NAME="${EVENT_NAME:-}"
REF="${REF:-}"
LABELS="${LABELS:-}"
HEAD="${HEAD:-HEAD}"
OUTPUT="${GITHUB_OUTPUT:-/dev/stdout}"
# a change in one of these paths requires to build the opengate_core wheels
# (main.yml: Geant4 and ITK versions, build jobs; the test action is not here)
CORE_PATHS=(core VERSION .github/workflows/actions_build .github/workflows/main.yml)

OSES=(ubuntu-24.04 macos-15 windows-2025)
ALL_PY=(3.10 3.11 3.12 3.13 3.14)
FEW_PY=(3.10 3.14)

is_tag=false
[[ "$REF" == refs/tags/* ]] && is_tag=true
has_label() { [[ ",$LABELS," == *",$1,"* ]]; }

# ---------------------------------------------------------------- matrix
pairs=()
for os in "${OSES[@]}"; do
  if [[ "$EVENT_NAME" == "schedule" || "$EVENT_NAME" == "workflow_dispatch" || "$is_tag" == true ]] ||
    has_label full-matrix; then
    py=("${ALL_PY[@]}")
  elif [[ "$EVENT_NAME" == "push" && "$os" != macos-* ]]; then
    py=("${ALL_PY[@]}")
  else
    py=("${FEW_PY[@]}")
  fi
  for v in "${py[@]}"; do
    pairs+=("$os $v")
  done
done
matrix=$(printf '%s\n' "${pairs[@]}" |
  awk 'BEGIN{printf "["} {printf "%s{\"os\":\"%s\",\"python-version\":\"%s\"}", (NR>1?",":""), $1, $2} END{printf "]"}')
echo "Matrix: $matrix"
echo "matrix=$matrix" >>"$OUTPUT"
# names of the wheel artifacts needed
needed=$(printf '%s\n' "${pairs[@]}" | awk '{print "dist-" $1 "-" $2 "-opengate-core"}' | sort)

# ---------------------------------------------------------------- reuse
build() {
  echo "Build the opengate_core wheels: $1"
  echo "reuse_run_id=" >>"$OUTPUT"
  exit 0
}

[[ "$EVENT_NAME" == "pull_request" || "$EVENT_NAME" == "push" ]] || build "event $EVENT_NAME"
[[ "$is_tag" == true ]] && build "tag $REF"
has_label build-core && build "label build-core"

# last master runs (push and schedule), most recent first
runs=$(gh api "repos/$REPO/actions/workflows/main.yml/runs?branch=master&per_page=50" \
  --jq '.workflow_runs[] | select(.event == "push" or .event == "schedule") | "\(.id) \(.head_sha)"') ||
  build "cannot list the master runs"

while read -r run_id sha; do
  [[ -n "$run_id" ]] || continue
  # same opengate_core sources as the commit tested here?
  git cat-file -e "$sha^{commit}" 2>/dev/null || continue
  git diff --quiet "$sha" "$HEAD" -- "${CORE_PATHS[@]}" || continue
  # all the needed wheels built and still available? (a wheel artifact is
  # uploaded at the end of its build job, so only if the build succeeded)
  available=$(gh api "repos/$REPO/actions/runs/$run_id/artifacts?per_page=100" \
    --jq '.artifacts[] | select((.name | endswith("-opengate-core")) and (.expired | not)) | .name' | sort)
  missing=$(comm -23 <(echo "$needed") <(echo "$available"))
  if [[ -z "$missing" ]]; then
    echo "Reuse the opengate_core wheels of the master run $run_id (commit $sha)"
    echo "reuse_run_id=$run_id" >>"$OUTPUT"
    exit 0
  fi
done <<<"$runs"

build "no recent master run with the same opengate_core sources and all the needed wheels"
