#!/bin/sh
# Build Gitea.alfredworkflow from ./source (only tracked/needed files, no caches).
set -eu
cd "$(dirname "$0")/source"
out="../Gitea.alfredworkflow"
rm -f "$out"
zip -q -r -X "$out" . -x '*.DS_Store' -x '*__pycache__*' -x '*.pyc' -x 'workflow/.alfredversionchecked'
echo "Built $(cd .. && pwd)/Gitea.alfredworkflow"
