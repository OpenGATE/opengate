#!/usr/bin/env bash
#
# For a pull request that does not change the opengate_core sources, find a
# master CI run whose opengate_core wheels can be reused instead of building
# them again (the build of the 15 wheels takes ~30 min).
#
# Prints "reuse_run_id=<id>" (empty if the wheels must be built) to
# $GITHUB_OUTPUT (or stdout when run locally).
#
# The wheels of a master run are reused only if the opengate_core sources
# (core/, VERSION, the build action and main.yml) are identical in that run
# and in the base of the pull request, and if the pull request does not
# change them.
#
# Environment:
#   EVENT_NAME  github.event_name (only "pull_request" can reuse wheels)
#   LABELS      labels of the pull request, comma separated: the label
#               "build-core" forces the build
#   BASE, HEAD  commits to compare (default: HEAD^1 and HEAD, i.e. the base and
#               the merge commit checked out for a pull request)
#   GH_TOKEN    token for the GitHub API (gh)

set -uo pipefail

REPO="${GITHUB_REPOSITORY:-OpenGATE/opengate}"
BASE="${BASE:-HEAD^1}"
HEAD="${HEAD:-HEAD}"
OUTPUT="${GITHUB_OUTPUT:-/dev/stdout}"
# a change in one of these paths requires to build the opengate_core wheels
# (main.yml: Geant4 and ITK versions, build jobs; the test action is not here)
CORE_PATHS=(core VERSION .github/workflows/actions_build .github/workflows/main.yml)
# number of build_opengate_core_wheel_pr jobs (3 OS x 5 python versions)
N_WHEELS=15

build() {
  echo "Build the opengate_core wheels: $1"
  echo "reuse_run_id=" >>"$OUTPUT"
  exit 0
}

[[ "${EVENT_NAME:-}" == "pull_request" ]] || build "not a pull request"
[[ ",${LABELS:-}," == *",build-core,"* ]] && build "label build-core"

changed=$(git diff --name-only "$BASE" "$HEAD" -- "${CORE_PATHS[@]}")
if [[ -n "$changed" ]]; then
  build "the pull request changes: $(echo $changed | head -c 300)"
fi

# last master runs (push), most recent first
runs=$(gh api "repos/$REPO/actions/workflows/main.yml/runs?branch=master&event=push&per_page=20" \
  --jq '.workflow_runs[] | "\(.id) \(.head_sha)"') || build "cannot list the master runs"

while read -r run_id sha; do
  [[ -n "$run_id" ]] || continue
  # same opengate_core sources as the base of the pull request?
  git cat-file -e "$sha^{commit}" 2>/dev/null || continue
  git diff --quiet "$sha" "$BASE" -- "${CORE_PATHS[@]}" || continue
  # all wheels built and still available?
  n_ok=$(gh api "repos/$REPO/actions/runs/$run_id/jobs?per_page=100" \
    --jq '[.jobs[] | select((.name | startswith("build_opengate_core_wheel_pr")) and .conclusion == "success")] | length')
  n_art=$(gh api "repos/$REPO/actions/runs/$run_id/artifacts?per_page=100" \
    --jq '[.artifacts[] | select((.name | endswith("-opengate-core")) and (.expired | not))] | length')
  if [[ "$n_ok" == "$N_WHEELS" && "$n_art" == "$N_WHEELS" ]]; then
    echo "Reuse the opengate_core wheels of the master run $run_id (commit $sha)"
    echo "reuse_run_id=$run_id" >>"$OUTPUT"
    exit 0
  fi
done <<<"$runs"

build "no recent master run with the same opengate_core sources and all wheels"
