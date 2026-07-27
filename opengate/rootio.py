"""Internal ROOT I/O infrastructure used by actor outputs and jobs merge.

This module is intentionally separate from ``opengate.contrib.root_helpers``.
The contrib helpers are user-facing utilities for ad hoc ROOT
post-processing, whereas the classes and helpers here are part of GATE's
internal actor-output persistence and merge machinery.
"""

from pathlib import Path

import awkward as ak
import numpy as np
import uproot


def _normalize_writable_branch_payload(branch_payload):
    """Convert one streamed ROOT chunk into uproot-writable arrays."""

    def _normalize_one_branch(value):
        if isinstance(value, np.ndarray):
            if value.dtype == object:
                value = value.tolist()
            if value.ndim == 0:
                return np.asarray([value.item()])
            return value
        try:
            len(value)
        except TypeError:
            value = [value]
        return ak.Array(value)

    return {k: _normalize_one_branch(v) for k, v in branch_payload.items()}


class RootMergeFileWriter:
    """Incremental ROOT writer used by split-job merge.

    The writer owns one physical ROOT file and keeps writable tree handles open
    so multiple actor outputs can stream chunks into distinct trees of the same
    file without repeatedly recreating it.
    """

    def __init__(self, output_path):
        self.output_path = Path(output_path)
        self._file = None
        self._trees = {}

    def open(self):
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = uproot.recreate(self.output_path)

    def create_tree(self, tree_name, branch_types):
        if self._file is None:
            raise RuntimeError(
                "RootMergeFileWriter.create_tree() called before open()."
            )
        if tree_name in self._trees:
            return self._trees[tree_name]
        tree = self._file.mktree(tree_name, branch_types)
        self._trees[tree_name] = tree
        return tree

    def append_chunk(self, tree_name, branch_payload):
        if tree_name not in self._trees:
            raise RuntimeError(
                f"RootMergeFileWriter.append_chunk() received unknown tree "
                f"'{tree_name}'. Call create_tree() first."
            )
        self._trees[tree_name].extend(
            _normalize_writable_branch_payload(branch_payload)
        )

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None
            self._trees = {}
