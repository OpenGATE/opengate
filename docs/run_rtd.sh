#!/usr/bin/env bash

# build the documentation locally in analogy to the ReadTheDocs workflow
TESTPATH=$1
cd $TESTPATH
rm -rf opengate
rm -rf venv
git clone --depth 1 https://github.com/OpenGATE/gam-gate.git opengate
cd opengate
git fetch origin --force --prune --prune-tags --depth 50 refs/heads/fix_autodoc:refs/remotes/origin/fix_autodoc
git checkout --force origin/fix_autodoc
python -mvirtualenv $TESTPATH/venv
source $TESTPATH/venv/bin/activate
python -m pip install --upgrade --no-cache-dir pip setuptools
python -m pip install --upgrade --no-cache-dir sphinx
python -m pip install --exists-action=w --no-cache-dir -r docs/requirements.txt
mkdir docs/output
cd docs/source
python -m sphinx -T -b html -d _build/doctrees -D language=en . ../output/html