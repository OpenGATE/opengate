"""Numpy output of digi collections: file names, and the writer used to merge
split jobs. The files themselves are written in C++ (GateDigiCollectionNumpyWriter).
"""

from collections import OrderedDict
from pathlib import Path

import numpy as np

# same as GateDigiCollectionNumpyWriter::kStringLength
STRING_LENGTH = 64

_ROW_COUNT_WIDTH = 20

_BRANCH_TYPE_TO_DTYPE = {
    "float64": "<f8",
    "int32": "<i4",
    "int64": "<i8",
    "string": f"|S{STRING_LENGTH}",
}


def is_numpy_path(path):
    return path is not None and Path(path).suffix == ".npy"


def numpy_tree_path(path, tree_name):
    """The file of one digi collection, e.g. hits.npy -> hits.Hits.npy"""
    path = Path(path)
    return path.with_name(f"{path.stem}.{tree_name}.npy")


def read_numpy_header(path):
    """Return (dtype, number of rows) without reading the data."""
    with open(path, "rb") as f:
        version = np.lib.format.read_magic(f)
        if version == (1, 0):
            shape, _, dtype = np.lib.format.read_array_header_1_0(f)
        else:
            shape, _, dtype = np.lib.format.read_array_header_2_0(f)
    return dtype, shape[0]


def _branch_type(dtype):
    if dtype.kind == "S":
        return "string"
    return dtype.name


def inspect_numpy_trees(path, tree_names):
    """Tree descriptors, like the ROOT metadata, of the files that exist."""
    trees = []
    for tree_name in tree_names:
        tree_path = numpy_tree_path(path, tree_name)
        if not tree_path.exists():
            continue
        dtype, _ = read_numpy_header(tree_path)
        branches = {name: _branch_type(dtype[name]) for name in dtype.names}
        trees.append({"tree_name": tree_name, "branches": branches})
    return trees


def iter_numpy_chunks(path, step_bytes=64 * 1024 * 1024):
    """Read a .npy file in blocks, as dicts of columns in file order."""
    if read_numpy_header(path)[1] == 0:
        return
    data = np.load(path, mmap_mode="r")
    step = max(1, step_bytes // data.dtype.itemsize)
    for start in range(0, len(data), step):
        block = data[start : start + step]
        yield OrderedDict((name, np.asarray(block[name])) for name in data.dtype.names)


class NumpyFileAppender:
    """Writes a .npy file block by block, the row count is set at close."""

    def __init__(self, path, branch_types):
        self.path = Path(path)
        self.branch_types = dict(branch_types)
        self.dtype = None
        self.number_of_rows = 0
        self._file = None
        self._row_count_position = None

    def _open(self, dtype):
        self.dtype = np.dtype(dtype)
        self._file = open(self.path, "wb")
        descr = np.lib.format.dtype_to_descr(self.dtype)
        before = "{'descr': " + repr(descr) + ", 'fortran_order': False, 'shape': ("
        after = ",), }"
        text_size = len(before) + _ROW_COUNT_WIDTH + len(after) + 1
        # the data starts at a multiple of 64 bytes, like numpy does
        version, prefix_size = 1, 10
        header_size = -(-(prefix_size + text_size) // 64) * 64 - prefix_size
        if header_size > 65535:
            version, prefix_size = 2, 12
            header_size = -(-(prefix_size + text_size) // 64) * 64 - prefix_size
        self._file.write(b"\x93NUMPY" + bytes([version, 0]))
        self._file.write(header_size.to_bytes(prefix_size - 8, "little"))
        self._file.write(before.encode("latin1"))
        self._row_count_position = self._file.tell()
        self._file.write(f"{0:>{_ROW_COUNT_WIDTH}}".encode("latin1"))
        padding = " " * (header_size - text_size)
        self._file.write((after + padding + "\n").encode("latin1"))

    def append(self, branch_payload):
        if self._file is None:
            # keep the column order and types of the first block
            self._open(
                [(k, np.asarray(v).dtype.str) for k, v in branch_payload.items()]
            )
        n = len(next(iter(branch_payload.values())))
        rows = np.empty(n, dtype=self.dtype)
        for name in self.dtype.names:
            rows[name] = branch_payload[name]
        self._file.write(rows.tobytes())
        self.number_of_rows += n

    def close(self):
        if self._file is None:
            # nothing was appended, write an empty array
            self._open(
                [(k, _BRANCH_TYPE_TO_DTYPE[v]) for k, v in self.branch_types.items()]
            )
        self._file.seek(self._row_count_position)
        self._file.write(f"{self.number_of_rows:>{_ROW_COUNT_WIDTH}}".encode("latin1"))
        self._file.close()
        self._file = None


class NumpyMergeFileWriter:
    """Same interface as RootMergeFileWriter, one .npy file per tree."""

    def __init__(self, output_path):
        self.output_path = Path(output_path)
        self._files = {}

    def open(self):
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def create_tree(self, tree_name, branch_types):
        if tree_name not in self._files:
            self._files[tree_name] = NumpyFileAppender(
                numpy_tree_path(self.output_path, tree_name), branch_types
            )
        return self._files[tree_name]

    def append_chunk(self, tree_name, branch_payload):
        if tree_name not in self._files:
            raise RuntimeError(
                f"NumpyMergeFileWriter.append_chunk() received unknown tree "
                f"'{tree_name}'. Call create_tree() first."
            )
        self._files[tree_name].append(branch_payload)

    def close(self):
        for f in self._files.values():
            f.close()
        self._files = {}


def create_merge_file_writer(output_path):
    """Writer for the merged output of split jobs, ROOT or numpy by suffix."""
    if is_numpy_path(output_path):
        return NumpyMergeFileWriter(output_path)
    from .rootio import RootMergeFileWriter

    return RootMergeFileWriter(output_path)
