"""Internal ROOT I/O infrastructure used by actor outputs and jobs merge.

This module is intentionally separate from ``opengate.contrib.root_helpers``.
The contrib helpers are user-facing utilities for ad hoc ROOT
post-processing, whereas the classes and helpers here are part of GATE's
internal actor-output persistence and merge machinery.
"""

from collections.abc import Mapping
from pathlib import Path

import awkward as ak
import numpy as np
import uproot


ROOT_COMPRESSION_ALGORITHMS = {
    "zlib": uproot.ZLIB,
    "lz4": uproot.LZ4,
    "zstd": uproot.ZSTD,
    "lzma": uproot.LZMA,
}


def normalize_root_output_compression(value):
    """Return a serializable ROOT compression specification.

    Accepted values are an algorithm name, an ``"algorithm:level"`` string,
    ``"none"``, or a mapping with ``algorithm`` and optional ``level`` entries.
    Keeping the public value free of uproot objects allows it to be persisted
    in a Simulation dictionary.
    """

    if isinstance(value, str):
        algorithm, separator, level = value.partition(":")
        value = {"algorithm": algorithm}
        if separator:
            try:
                value["level"] = int(level)
            except ValueError as error:
                raise ValueError(
                    f"Invalid ROOT compression level in '{algorithm}:{level}'."
                ) from error
    if not isinstance(value, Mapping):
        raise TypeError(
            "ROOT output compression must be an algorithm name or a mapping "
            "with 'algorithm' and optional 'level' entries."
        )
    unknown_keys = set(value) - {"algorithm", "level"}
    if unknown_keys:
        raise ValueError(
            f"Unknown ROOT output compression entries: {sorted(unknown_keys)}."
        )
    algorithm = str(value.get("algorithm", "")).lower()
    if algorithm == "none":
        if value.get("level") is not None:
            raise ValueError("ROOT compression algorithm 'none' has no level.")
        return {"algorithm": "none", "level": None}
    if algorithm not in ROOT_COMPRESSION_ALGORITHMS:
        raise ValueError(
            f"Unknown ROOT compression algorithm '{algorithm}'. Expected one of "
            f"{sorted((*ROOT_COMPRESSION_ALGORITHMS, 'none'))}."
        )
    level = int(value.get("level", 1))
    # Let uproot enforce the algorithm-specific level range.
    ROOT_COMPRESSION_ALGORITHMS[algorithm](level)
    return {"algorithm": algorithm, "level": level}


def make_uproot_compression(value):
    """Convert a serializable compression specification for uproot writing."""

    specification = normalize_root_output_compression(value)
    if specification["algorithm"] == "none":
        return None
    return ROOT_COMPRESSION_ALGORITHMS[specification["algorithm"]](
        specification["level"]
    )


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

    def __init__(self, output_path, compression="zlib"):
        self.output_path = Path(output_path)
        self.compression = normalize_root_output_compression(compression)
        self._file = None
        self._trees = {}

    def open(self):
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = uproot.recreate(
            self.output_path,
            compression=make_uproot_compression(self.compression),
        )

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
