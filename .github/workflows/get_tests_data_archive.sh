#!/bin/bash
# Download the opengate test data archive (GitLab job artifacts zip) for a given
# commit of the test data repository, with retries.
# Usage: get_tests_data_archive.sh <data_commit> <output_file>
set -euo pipefail

sha=$1
out=$2
api=https://gitlab.in2p3.fr/api/v4/projects/15155

get() {
    curl -fsSL --retry 5 --retry-delay 30 --retry-all-errors --connect-timeout 60 "$@"
}

pipeline=$(get "$api/repository/commits/$sha" | jq -r .last_pipeline.id)
if [[ -z "$pipeline" || "$pipeline" == "null" ]]; then
    echo "No GitLab pipeline found for test data commit $sha"
    exit 1
fi
job=$(get "$api/pipelines/$pipeline/jobs" | jq -r '.[0].id')
if [[ -z "$job" || "$job" == "null" ]]; then
    echo "No GitLab job found for pipeline $pipeline"
    exit 1
fi

mkdir -p "$(dirname "$out")"
echo "Downloading test data $sha (pipeline $pipeline, job $job)"
get -o "$out" "$api/jobs/$job/artifacts"
ls -lh "$out"
