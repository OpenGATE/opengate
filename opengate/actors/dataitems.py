"""Data items and data containers used by actor outputs.

This module defines the Python-side runtime objects that actor outputs use to
hold, process, merge, and sometimes write scored data.

Core concepts:

- ``DataItem`` wraps one actual payload object such as an ITK image, a numpy
  array, or a Box-like dictionary. A DataItem is meant to feel as much as
  possible like that payload while adding GATE-specific behavior such as merge
  semantics, metadata handling, writing, and derived quantities.

- ``DataItemContainer`` groups one or more DataItems into the structural unit
  managed by an actor output. Containers are used when one logical actor output
  is backed by multiple items, for example a value image plus a squared-value
  image, or a value image plus derived quantities such as uncertainty.

- ``ActorOutputUsingDataItemContainer`` owns concrete container instances for
  merged data and per-run data. The actor output is responsible for item-level
  configuration such as activation, output filenames, and persistence, while
  DataItems and DataItemContainers provide the payload behavior and structural
  organization underneath.

In short: DataItems model enhanced payload objects, DataItemContainers model
structured collections of such items, and actor outputs coordinate their use in
the simulation workflow.
"""

import itk
import numpy as np
import json
import os
import platform
import tempfile
from pathlib import Path
from collections import OrderedDict
from box import Box

from ..exception import (
    fatal,
    warning,
    GateImplementationError,
    GateDeprecationError,
)
from ..serialization import dump_json
from ..utility import ensure_filename_is_str, calculate_variance
from ..utility import g4_best_unit_tuple, g4_units
from ..utility import insert_suffix_before_extension
from ..image import (
    sum_itk_images,
    divide_itk_images,
    multiply_itk_images,
    scale_itk_image,
    copy_itk_image,
    create_3d_image,
    write_itk_image,
    get_info_from_image,
    itk_image_from_array,
    add_constant_to_itk_image,
)
from ..rootio import RootMergeFileWriter
from ..contrib.root_helpers import root_write_tree


def derived_data_item(*, depends_on):
    """Declare a property as a derived data item backed by primary items.

    The decorator stores dependency metadata on the property's getter so a
    small class-processing pass at module import time can collect inherited
    derived items and resolve which primary items must be persisted to
    reconstruct them later.
    """

    depends_on = tuple(depends_on)

    def decorator(func):
        func._gate_is_derived_data_item = True
        func._gate_derived_item_name = func.__name__
        func._gate_depends_on = depends_on
        return property(func)

    return decorator


def _raise_pre_interface_convenience_deprecation(container_cls_name, shortcut_name):
    raise GateDeprecationError(
        f"The convenience shortcut '{shortcut_name}' on container class "
        f"'{container_cls_name}' is temporarily disabled on purpose. "
        f"Origin: this shortcut stems from the pre-interface actor-output era, "
        f"when containers had to provide both structural storage and much of the "
        f"user-facing convenience API. With actor interfaces now in place, these "
        f"shortcuts are being audited and may move upward in the architecture. "
        f"This exception is an intentional probe to identify remaining call sites."
    )


class DataItem:
    """This is the base class for all data items.
    It stores the actual data, e.g. an array, an image, etc. in an attribute 'data'.

    Derived classes can (should) implement merge_with and inplace_merge_with
    so actor output using this data container with the respective data items can be merged after runs.

    Derived classes should also implement an appropriate write method
    if data writing is supposed to be handled on the python-side.

    Derived classes can also implement arithmetic operator like __add__, __mul__, etc.
    """

    def __init__(self, *args, data=None, meta_data=None, **kwargs):
        self.data = None
        self._owner_container = None
        if data is not None:
            self.set_data(data)
        self.meta_data = Box()
        if meta_data:
            try:
                for k, v in meta_data.items():
                    self.meta_data[k] = v
            except AttributeError:
                fatal(
                    f"Illegal keyword argument meta_data: {meta_data}. "
                    f"Should be a dictionary-like object, but found {type(meta_data)}."
                )

    def set_data(self, data, **kwargs):
        self.data = data

    @property
    def data_is_none(self):
        return self.data is None

    def _assert_data_is_not_none(self):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )

    def __add__(self, other):
        return NotImplemented

    def __iadd__(self, other):
        return NotImplemented

    def __mul__(self, other):
        return NotImplemented

    def __imul__(self, other):
        return NotImplemented

    def __truediv__(self, other):
        return NotImplemented

    def __getattr__(self, item):
        # Design rationale: a DataItem should feel as much as possible like the
        # payload it wraps, while adding GATE-specific behavior such as merge
        # semantics, metadata, writing, or derived quantities. Hand down
        # unknown attributes and methods to the wrapped payload so callers can
        # use the DataItem as an enhanced image / array / Box instead of
        # constantly unwrapping ``.data``.
        #
        # This transparency is intentional at the DataItem layer. It is more
        # problematic at the DataItemContainer layer, where multiplicity and
        # item identity should remain explicit.
        #
        # Exclude 'data' to avoid infinite recursion, and exclude
        # '__setstate__' / '__getstate__' to avoid interference with pickling.
        if item not in ("data", "__setstate__", "__getstate__"):
            if hasattr(self.data, item):
                attribute = getattr(self.data, item)
                if callable(attribute):

                    def hand_down(*args, **kwargs):
                        getattr(self.data, item)(*args, **kwargs)

                    return hand_down
                return attribute
            else:
                raise AttributeError(f"No such attribute '{item}'")
        else:
            raise AttributeError(f"No such attribute '{item}'")

    def merge_with(self, other):
        """The base class does not implement merging.
        Specific classes can override this, e.g. to merge mean values.
        """
        raise NotImplementedError(
            f"Method 'inplace_merge_with' not implemented for data item class {type(self)} "
        )

    def inplace_merge_with(self, other):
        """The base class does not implement merging.
        Specific classes can override this, e.g. to merge mean values.
        """
        raise NotImplementedError(
            f"Method 'inplace_merge_with' not implemented for data item class {type(self)} "
        )

    def write(self, *args, **kwargs):
        raise NotImplementedError(f"This is the base class. ")

    def load(self, path, **kwargs):
        raise NotImplementedError(f"This is the base class. ")

    def clear_data(self):
        self.data = None

    def close_data(self):
        self.clear_data()

    def set_owner_container(self, owner_container):
        self._owner_container = owner_container

    def get_owner_container(self):
        return getattr(self, "_owner_container", None)


class SampleCountingDataItemMixin:
    """Mixin for data items that explicitly track how many samples they represent."""

    def __init__(self, *args, number_of_samples=1, **kwargs):
        self._number_of_samples = int(number_of_samples)
        super().__init__(*args, **kwargs)

    @property
    def number_of_samples(self):
        return self._number_of_samples

    @number_of_samples.setter
    def number_of_samples(self, value):
        self._number_of_samples = int(value)


def _get_sample_count_metadata_path(path):
    """Return the sidecar path used to persist sample counts for image items.

    Split-job merge may rehydrate image-based outputs from disk before derived
    quantities such as uncertainty are reconstructed. The corresponding primary
    images therefore need their ``number_of_samples`` value to survive the
    write/load round-trip.
    """

    return Path(insert_suffix_before_extension(Path(path), "samples")).with_suffix(
        Path(path).suffix + ".json"
    )


class MeanValueDataItemMixin:
    """This class cannot be instantiated on its own.
    It is solely meant to be mixed into a class that inherits from DataItem (or daughters).
    Important: It must appear before the main base class in the inheritance order so that the
    overloaded methods take priority.
    """

    # hints for IDE
    number_of_samples: int

    def merge_with(self, other):
        result = (self * self.number_of_samples + other * other.number_of_samples) / (
            self.number_of_samples + other.number_of_samples
        )
        result.number_of_samples = self.number_of_samples + other.number_of_samples
        return result

    def inplace_merge_with(self, other):
        if self.data is None:
            self.set_data(other.data)
            self.number_of_samples = other.number_of_samples
        else:
            self *= self.number_of_samples
            other *= other.number_of_samples
            self += other
            self /= self.number_of_samples + other.number_of_samples
            self.number_of_samples = self.number_of_samples + other.number_of_samples
        return self


class ArithmeticDataItem(DataItem):
    """Base class for data items where the data component already has implemented arithmetic operators.
    Examples: Scalars, Numpy arrays, etc.
    """

    def __iadd__(self, other):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )
        self.set_data(self.data + other.data)
        return self

    def __add__(self, other):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )
        return type(self)(data=self.data + other.data)

    def __mul__(self, other):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )
        return type(self)(data=self.data * other.data)

    def __imul__(self, other):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )
        self.set_data(self.data * other.data)
        return self

    def __truediv__(self, other):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )
        return type(self)(data=self.data / other.data)

    def __itruediv__(self, other):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )
        self.set_data(self.data / other.data)
        return self

    def write(self, path, **kwargs):
        np.savetxt(path, self.data)


# data items holding arrays
class ArrayDataItem(ArithmeticDataItem):

    def set_data(self, data):
        super().set_data(np.asarray(data))


class TimeCountSeriesDataItem(DataItem):
    """Sparse cumulative time series keyed by molecule/reaction label.

    The internal payload is a dictionary:
        label -> structured numpy array with fields ('time', 'count')
    """

    _required_dtype_names = ("time", "count")

    def set_data(self, data):
        if data is None:
            self.data = None
            return
        try:
            items = data.items()
        except AttributeError:
            fatal(
                f"TimeCountSeriesDataItem expects a dictionary-like object, "
                f"but got {type(data).__name__}."
            )
        processed = {}
        for key, value in items:
            arr = np.asarray(value)
            if arr.dtype.names != self._required_dtype_names:
                fatal(
                    f"TimeCountSeriesDataItem expects structured numpy arrays with "
                    f"fields {self._required_dtype_names}, but key '{key}' has dtype "
                    f"{arr.dtype}."
                )
            processed[str(key)] = arr
        self.data = processed

    def inplace_merge_with(self, other):
        if other is None or other.data is None:
            return self
        if self.data is None:
            self.set_data(other.data)
            return self
        merged = dict(self.data)
        for key, other_series in other.data.items():
            if key in merged:
                base_series = merged[key]
                if len(base_series) > 0:
                    offset = int(base_series["count"][-1])
                else:
                    offset = 0
                appended = np.empty_like(other_series)
                appended["time"] = other_series["time"]
                appended["count"] = other_series["count"] + offset
                merged[key] = np.concatenate((base_series, appended))
            else:
                merged[key] = other_series.copy()
        self.data = merged
        return self

    def merge_with(self, other):
        result = type(self)()
        if self.data is not None:
            result.set_data(self.data)
        return result.inplace_merge_with(other)

    def write(self, *args, **kwargs):
        raise NotImplementedError(
            "Writing of chemistry counter time-count series is not implemented yet."
        )


class ScalarDataItem(ArithmeticDataItem):

    def write(self, *args, **kwargs):
        raise NotImplementedError


class StatisticsDataItem(DataItem):
    """Semantic data item for simulation statistics.

    The payload is a Box-like dictionary whose entries have dedicated merge
    semantics. Merging therefore happens here, not based on Python scalar
    types, because `int` and `float` alone do not tell us whether a field
    should be summed, minimized, maximized, or otherwise combined.
    """

    def set_data(self, data, **kwargs):
        """The input data must behave like a dictionary."""
        self.reset_data()
        self.data.update(data)

    def reset_data(self):
        self.data = Box()
        self.data.runs = 0
        self.data.events = 0
        self.data.tracks = 0
        self.data.steps = 0
        self.data.duration = 0
        self.data.start_time = 0
        self.data.stop_time = 0
        self.data.sim_start_time = 0
        self.data.sim_stop_time = 0
        self.data.init = 0
        self.data.track_types = {}
        self.data.nb_threads = 1

    @classmethod
    def get_known_entry_names(cls):
        stats_data_item = cls()
        stats_data_item.reset_data()
        return tuple(stats_data_item.data.keys())

    def __getattr__(self, item):
        # StatisticsDataItem is the semantic access layer for statistics:
        # some quantities are stored directly in the Box payload (events,
        # tracks, track_types, ...), while others are derived as properties on
        # this class (pps, tps, sps, ...). Allow callers to access the raw
        # payload entries transparently from the data item itself.
        if item not in ("data", "__setstate__", "__getstate__"):
            try:
                return self.data[item]
            except (TypeError, KeyError):
                pass
        raise AttributeError(f"No such attribute '{item}'")

    @property
    def pps(self):
        if self.data.duration != 0:
            return int(self.data.events / (self.data.duration / g4_units.s))
        return 0

    @property
    def tps(self):
        if self.data.duration != 0:
            return int(self.data.tracks / (self.data.duration / g4_units.s))
        return 0

    @property
    def sps(self):
        if self.data.duration != 0:
            return int(self.data.steps / (self.data.duration / g4_units.s))
        return 0

    def get_processed_output(self):
        d = {}
        d["runs"] = {"value": self.data.runs, "unit": None}
        d["events"] = {"value": self.data.events, "unit": None}
        d["tracks"] = {"value": self.data.tracks, "unit": None}
        d["steps"] = {"value": self.data.steps, "unit": None}
        val, unit = g4_best_unit_tuple(self.data.init, "Time")
        d["init"] = {"value": val, "unit": unit}
        val, unit = g4_best_unit_tuple(self.data.duration, "Time")
        d["duration"] = {"value": val, "unit": unit}
        d["pps"] = {"value": self.pps, "unit": None}
        d["tps"] = {"value": self.tps, "unit": None}
        d["sps"] = {"value": self.sps, "unit": None}
        d["start_time"] = {"value": self.data.start_time, "unit": None}
        d["stop_time"] = {"value": self.data.stop_time, "unit": None}
        val, unit = g4_best_unit_tuple(self.data.sim_start_time, "Time")
        d["sim_start_time"] = {"value": val, "unit": unit}
        val, unit = g4_best_unit_tuple(self.data.sim_stop_time, "Time")
        d["sim_stop_time"] = {"value": val, "unit": unit}
        d["threads"] = {"value": self.data.nb_threads, "unit": None}
        d["arch"] = {"value": platform.system(), "unit": None}
        d["python"] = {"value": platform.python_version(), "unit": None}
        d["track_types"] = {"value": self.data.track_types, "unit": None}
        return d

    def __str__(self):
        s = ""
        for k, v in self.get_processed_output().items():
            if k == "track_types":
                if len(v["value"]) > 0:
                    s += "track_types\n"
                    for t, n in v["value"].items():
                        s += f"{' ' * 24}{t}: {n}\n"
            else:
                unit = "" if v["unit"] is None else str(v["unit"])
                s += f"{k}{' ' * (20 - len(k))}{v['value']} {unit}\n"
        return s.rstrip("\n")

    def inplace_merge_with(self, *other):
        if self.data is None:
            self.reset_data()

        for o in other:
            self.data.runs += o.data.runs
            self.data.events += o.data.events
            self.data.tracks += o.data.tracks
            self.data.steps += o.data.steps
            self.data.duration += o.data.duration
            self.data.init += o.data.init

            common_entries = set(self.data.track_types.keys()).intersection(
                o.data.track_types.keys()
            )
            new_entries = set(o.data.track_types.keys()).difference(
                self.data.track_types.keys()
            )
            for k in common_entries:
                self.data.track_types[k] += o.data.track_types[k]
            for k in new_entries:
                self.data.track_types[k] = o.data.track_types[k]

        if len(other) > 0:
            self.data.start_time = min([o.data.start_time for o in other])
            self.data.stop_time = max([o.data.stop_time for o in other])
            self.data.sim_start_time = min([o.data.sim_start_time for o in other])
            self.data.sim_stop_time = max([o.data.sim_stop_time for o in other])
        return self

    def merge_with(self, other):
        merged = type(self)()
        if self.data is not None:
            merged.set_data(self.data)
        return merged.inplace_merge_with(other)

    def write(self, path, encoder="json", **kwargs):
        with open(path, "w+") as f:
            if encoder == "json":
                dump_json(self.get_processed_output(), f, indent=4)
            else:
                f.write(self.__str__())

    def load(self, path, **kwargs):
        with open(path, "r") as input_file:
            processed_output = json.load(input_file)
        loaded_data = {}
        for key, entry in processed_output.items():
            loaded_data[key] = entry["value"]
            unit = entry["unit"]
            if unit in g4_units:
                loaded_data[key] *= g4_units[unit]
        self.set_data(loaded_data)


class RootDataItem(DataItem):
    """Metadata-backed handle for ROOT actor output.

    Phase 1 intentionally focuses on the common single-tree case. Metadata is
    inspected from the already-written ROOT file, persisted to JSON, and later
    reused during split-job merging.
    """

    metadata_version = 1

    def __init__(self, *args, **kwargs):
        self._root_file = None
        self.root_meta_data = None
        super().__init__(*args, **kwargs)

    def set_root_meta_data(self, meta_data):
        self.root_meta_data = Box(meta_data)

    def capture_empty_runtime_metadata(
        self,
        root_file_path,
        actor_name,
        actor_type,
        actor_output_name,
        requested_attributes=None,
        skipped_attributes=None,
    ):
        """Persist the legitimate 'configured but no ROOT file' outcome.

        Some ROOT-backed actors may finish a run without having produced any
        entries. In that case, no ROOT file can be inspected, but merge logic
        still needs authoritative metadata stating that this child contributes
        no ROOT payload rather than representing a broken run.
        """
        root_file_path = Path(root_file_path)
        self.set_root_meta_data(
            {
                "metadata_version": self.metadata_version,
                "actor_name": actor_name,
                "actor_type": actor_type,
                "actor_output_name": actor_output_name,
                "root_output_path": str(root_file_path),
                "requested_attributes": requested_attributes,
                "skipped_attributes": skipped_attributes,
                "expected_on_disk": True,
                "root_file_written": False,
                "number_of_entries": 0,
                "trees": [],
                "merge_sources": [],
            }
        )

    def _resolve_expected_tree_names_from_owner(self):
        owner_container = self.get_owner_container()
        if owner_container is None:
            raise GateImplementationError(
                "Cannot resolve ROOT tree names because this RootDataItem has no owning container."
            )
        actor_output = getattr(owner_container, "belongs_to", None)
        if actor_output is None:
            raise GateImplementationError(
                "Cannot resolve ROOT tree names because the owning container is not bound to an actor output."
            )
        runtime_getter = getattr(actor_output, "_get_runtime_tree_names", None)
        if runtime_getter is None:
            raise GateImplementationError(
                "Cannot resolve ROOT tree names because the owning actor output does not provide runtime ROOT tree-name discovery."
            )
        tree_names = runtime_getter()
        if not tree_names:
            raise GateImplementationError(
                "Cannot resolve ROOT tree names because neither persisted metadata nor live actor-output tree names are available."
            )
        return tree_names

    def has_root_meta_data(self):
        return self.root_meta_data is not None

    def root_file_was_written(self):
        if not self.has_root_meta_data():
            return None
        return self.root_meta_data.get("root_file_written")

    @staticmethod
    def _strip_root_cycle(key):
        return key.split(";")[0]

    @staticmethod
    def _is_tree(root_object):
        return hasattr(root_object, "arrays") and hasattr(root_object, "keys")

    @staticmethod
    def _is_string_branch_type(branch_type_name):
        branch_type_name = str(branch_type_name).lower()
        return "string" in branch_type_name or "char*" in branch_type_name

    @classmethod
    def inspect_root_file(cls, root_file_path, expected_tree_names=None):
        import uproot

        root_file_path = Path(root_file_path)
        if expected_tree_names is not None:
            expected_tree_names = set(expected_tree_names)
        with uproot.open(root_file_path) as root_file:
            trees = []
            for key in root_file.keys():
                tree_name = cls._strip_root_cycle(key)
                if (
                    expected_tree_names is not None
                    and tree_name not in expected_tree_names
                ):
                    continue
                root_object = root_file[tree_name]
                if not cls._is_tree(root_object):
                    continue
                branch_types = {}
                for branch_name in root_object.keys():
                    branch = root_object[branch_name]
                    branch_types[branch_name] = getattr(
                        branch,
                        "typename",
                        str(getattr(branch, "interpretation", "unknown")),
                    )
                trees.append({"tree_name": tree_name, "branches": branch_types})
        return trees

    def capture_runtime_metadata(
        self,
        root_file_path,
        actor_name,
        actor_type,
        actor_output_name,
        tree_descriptors=None,
        tree_names=None,
        requested_attributes=None,
        skipped_attributes=None,
    ):
        root_file_path = Path(root_file_path)
        if tree_descriptors is None:
            tree_name_description = (
                f"expected trees {list(tree_names)}"
                if tree_names is not None
                else f"actor '{actor_name}'"
            )
            fatal(
                "Cannot capture ROOT runtime metadata without explicit runtime "
                f"tree descriptors for {tree_name_description}."
            )
        if len(tree_descriptors) == 0:
            tree_name_description = (
                f"expected trees {list(tree_names)}"
                if tree_names is not None
                else f"actor '{actor_name}'"
            )
            fatal(
                f"Cannot capture ROOT metadata for {tree_name_description} "
                f"in '{root_file_path}'."
            )
        self.set_root_meta_data(
            {
                "metadata_version": self.metadata_version,
                "actor_name": actor_name,
                "actor_type": actor_type,
                "actor_output_name": actor_output_name,
                "root_output_path": str(root_file_path),
                "requested_attributes": requested_attributes,
                "skipped_attributes": skipped_attributes,
                "expected_on_disk": True,
                "root_file_written": True,
                "number_of_entries": None,
                "trees": tree_descriptors,
                "merge_sources": [],
            }
        )

    def save_root_metadata(self, path):
        if not self.has_root_meta_data():
            fatal(
                "Cannot save ROOT metadata because no ROOT metadata has been captured yet."
            )
        with open(path, "w") as output_file:
            dump_json(dict(self.root_meta_data), output_file, indent=4)

    def load_root_metadata(self, path):
        with open(path, "r") as input_file:
            self.set_root_meta_data(json.load(input_file))

    def load(self, path, metadata_path=None, load_mode="live", **kwargs):
        import uproot

        root_file_path = Path(path)
        self.close_data()
        if metadata_path is not None and Path(metadata_path).exists():
            self.load_root_metadata(metadata_path)
            if self.root_file_was_written() is False:
                self.root_meta_data["root_output_path"] = str(root_file_path)
                return
        elif not self.has_root_meta_data():
            if load_mode == "rehydrated":
                fatal(
                    "Cannot load ROOT output in load_mode='rehydrated' without "
                    f"a persisted metadata file. Missing metadata path: {metadata_path}."
                )
            if load_mode == "live":
                tree_names = self._resolve_expected_tree_names_from_owner()
                tree_descriptors = self.inspect_root_file(
                    root_file_path, expected_tree_names=tree_names
                )
                if len(tree_descriptors) == 0:
                    fatal(
                        "Cannot load ROOT metadata fallback because none of the "
                        f"expected trees {list(tree_names)} were found in "
                        f"'{root_file_path}'."
                    )
                self.set_root_meta_data(
                    {
                        "metadata_version": self.metadata_version,
                        "root_output_path": str(root_file_path),
                        "expected_on_disk": True,
                        "root_file_written": True,
                        "number_of_entries": None,
                        "trees": tree_descriptors,
                        "merge_sources": [],
                    }
                )
            else:
                fatal(
                    f"Unknown load_mode '{load_mode}' for RootDataItem.load(). "
                    "Known modes are 'live' and 'rehydrated'."
                )
        else:
            self.root_meta_data["root_output_path"] = str(root_file_path)

        self._root_file = uproot.open(root_file_path)

    def close_data(self):
        if self._root_file is not None:
            close_method = getattr(self._root_file, "close", None)
            if callable(close_method):
                close_method()
            self._root_file = None
        self.clear_data()

    def get_single_tree_descriptor(self):
        try:
            trees = self.root_meta_data["trees"]
        except (TypeError, KeyError):
            fatal("ROOT metadata does not contain any tree information.")
        if len(trees) != 1:
            raise NotImplementedError(
                "ROOT merge currently supports only single-tree actor outputs. "
                f"Found {len(trees)} trees in ROOT metadata."
            )
        return trees[0]

    def register_merge_source(self, source_item, run_id_from, run_id_to):
        if not self.has_root_meta_data():
            self.set_root_meta_data(
                {
                    "metadata_version": self.metadata_version,
                    "trees": source_item.root_meta_data["trees"],
                    "merge_sources": [],
                }
            )
        source_tree = source_item.get_single_tree_descriptor()
        target_tree = self.get_single_tree_descriptor()
        if set(source_tree["branches"].keys()) != set(target_tree["branches"].keys()):
            raise GateImplementationError(
                "Cannot merge ROOT trees with different branch names. "
                f"Target branches are {sorted(target_tree['branches'].keys())}, "
                f"source branches are {sorted(source_tree['branches'].keys())}."
            )
        root_output_path = source_item.root_meta_data["root_output_path"]
        merge_sources = self.root_meta_data.setdefault("merge_sources", [])
        for merge_source in merge_sources:
            if merge_source["root_output_path"] == root_output_path:
                merge_source.setdefault("run_id_map", {})[str(int(run_id_from))] = int(
                    run_id_to
                )
                return
        merge_sources.append(
            {
                "root_output_path": root_output_path,
                "run_id_map": {str(int(run_id_from)): int(run_id_to)},
            }
        )

    def _read_filtered_branch_data(self, source_tree, branch_names, run_id_from):
        branch_data = {}
        selection = None
        if "RunID" in branch_names:
            run_ids = source_tree["RunID"].array(library="np")
            selection = run_ids.astype(int) == int(run_id_from)
        for branch_name in branch_names:
            branch_values = source_tree[branch_name].array(library="np")
            if selection is None:
                branch_data[branch_name] = branch_values
            else:
                branch_data[branch_name] = branch_values[selection]
        return branch_data

    def _build_merged_branch_payload(self):
        # DEPRECATED: eager whole-tree accumulation for ROOT merge. Kept
        # temporarily during the streamed-merge refactor as a fallback/reference
        # implementation and should be removed once the chunked writer path is
        # the only active implementation.
        import uproot

        tree_descriptor = self.get_single_tree_descriptor()
        branch_types = tree_descriptor["branches"]
        branch_names = list(branch_types.keys())
        merged_numeric = {branch_name: [] for branch_name in branch_names}
        merged_strings = {branch_name: [] for branch_name in branch_names}
        current_event_offset = 0
        remap_run_ids = "RunID" in branch_names
        remap_event_ids = "EventID" in branch_names

        for merge_source in self.root_meta_data.get("merge_sources", []):
            run_id_map = {
                int(local_run_id): int(original_run_id)
                for local_run_id, original_run_id in merge_source.get(
                    "run_id_map", {}
                ).items()
            }
            if len(run_id_map) != 1:
                raise GateImplementationError(
                    "Legacy eager ROOT merge only supports one local->original "
                    "RunID mapping per merge source entry. Use the streamed "
                    "merge path for multi-run child contributions."
                )
            run_id_from, run_id_to = next(iter(run_id_map.items()))
            with uproot.open(merge_source["root_output_path"]) as root_file:
                source_tree = root_file[tree_descriptor["tree_name"]]
                branch_data = self._read_filtered_branch_data(
                    source_tree,
                    branch_names,
                    run_id_from,
                )

            for branch_name, branch_values in branch_data.items():
                if branch_name == "RunID" and remap_run_ids:
                    branch_values = np.full(
                        len(branch_values),
                        int(run_id_to),
                        dtype=branch_values.dtype,
                    )
                elif (
                    branch_name == "EventID"
                    and remap_event_ids
                    and len(branch_values) > 0
                ):
                    branch_values = branch_values + current_event_offset
                    current_event_offset = int(np.max(branch_values)) + 1

                if self._is_string_branch_type(branch_types[branch_name]):
                    merged_strings[branch_name].extend(branch_values.tolist())
                else:
                    merged_numeric[branch_name].append(branch_values)

        merged_branch_payload = {}
        for branch_name in branch_names:
            if self._is_string_branch_type(branch_types[branch_name]):
                merged_branch_payload[branch_name] = merged_strings[branch_name]
            else:
                chunks = merged_numeric[branch_name]
                if len(chunks) == 0:
                    merged_branch_payload[branch_name] = np.array([])
                elif len(chunks) == 1:
                    merged_branch_payload[branch_name] = chunks[0]
                else:
                    merged_branch_payload[branch_name] = np.concatenate(chunks)
        return tree_descriptor["tree_name"], merged_branch_payload

    @classmethod
    def _read_all_tree_payloads(cls, root_file_path):
        # DEPRECATED: eager whole-file reread helper used by the legacy ROOT
        # merge path. Streamed merge should write grouped target files once and
        # avoid reloading existing trees into memory.
        import uproot

        tree_payloads = {}
        root_file_path = Path(root_file_path)
        with uproot.open(root_file_path) as root_file:
            for tree_descriptor in cls.inspect_root_file(root_file_path):
                tree_name = tree_descriptor["tree_name"]
                tree = root_file[tree_name]
                branch_payload = {}
                for branch_name in tree_descriptor["branches"]:
                    branch_payload[branch_name] = tree[branch_name].array(library="ak")
                tree_payloads[tree_name] = {
                    "branches": tree_descriptor["branches"],
                    "payload": branch_payload,
                }
        return tree_payloads

    @classmethod
    def _rewrite_root_file_with_tree(
        cls, output_path, tree_name, branch_types, branch_payload
    ):
        # DEPRECATED: eager whole-file rewrite helper used by the legacy ROOT
        # merge path. Streamed merge should keep one writable ROOT file open and
        # append chunks directly into each target tree.
        output_path = Path(output_path)
        existing_trees = {}
        if output_path.exists():
            existing_trees = cls._read_all_tree_payloads(output_path)
        existing_trees[tree_name] = {
            "branches": branch_types,
            "payload": branch_payload,
        }

        with tempfile.NamedTemporaryFile(
            suffix=".root", dir=output_path.parent, delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        try:
            import uproot

            # DEBUG: dump branch payload structure before rewriting the shared
            # ROOT file. This helps diagnose cases where uproot receives an
            # unsized/scalar-like payload instead of a proper per-entry array.
            print("DEBUG RootDataItem._rewrite_root_file_with_tree payload inventory:")
            print(f"  output_path: {output_path}")
            print(f"  target_tree_name: {tree_name}")
            for existing_tree_name, existing_tree_data in existing_trees.items():
                print(f"  tree: {existing_tree_name}")
                print(
                    f"    declared branches: {list(existing_tree_data['branches'].keys())}"
                )
                for branch_name, branch_payload_value in existing_tree_data[
                    "payload"
                ].items():
                    payload_type = type(branch_payload_value).__name__
                    payload_shape = getattr(branch_payload_value, "shape", None)
                    try:
                        payload_length = len(branch_payload_value)
                    except Exception as error:
                        payload_length = (
                            f"<len failed: {type(error).__name__}: {error}>"
                        )
                    try:
                        preview = branch_payload_value[:3]
                    except Exception as error:
                        preview = f"<preview failed: {type(error).__name__}: {error}>"
                    print(f"    branch: {branch_name}")
                    print(f"      type: {payload_type}")
                    print(f"      shape: {payload_shape}")
                    print(f"      len: {payload_length}")
                    print(f"      preview: {preview}")

            with uproot.recreate(temporary_path) as output_file:
                for existing_tree_name, existing_tree_data in existing_trees.items():
                    root_write_tree(
                        output_file,
                        existing_tree_name,
                        existing_tree_data["branches"],
                        existing_tree_data["payload"],
                    )
            os.replace(temporary_path, output_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def write(self, path, metadata_path=None, **kwargs):
        # DEPRECATED: RootDataItem.write() reflects the legacy eager ROOT merge
        # path. Grouped file-level streamed merge should be driven from
        # Simulation.finalize_merge() via RootMergeFileWriter instead.
        if not self.has_root_meta_data():
            fatal(
                "Cannot write merged ROOT output because no ROOT metadata is available."
            )
        if len(self.root_meta_data.get("merge_sources", [])) == 0:
            return

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree_name, merged_branch_payload = self._build_merged_branch_payload()
        tree_descriptor = self.get_single_tree_descriptor()
        self._rewrite_root_file_with_tree(
            output_path,
            tree_name,
            tree_descriptor["branches"],
            merged_branch_payload,
        )

        self.capture_runtime_metadata(
            output_path,
            actor_name=self.root_meta_data.get("actor_name", "unknown_actor"),
            actor_type=self.root_meta_data.get("actor_type", "unknown_type"),
            actor_output_name=self.root_meta_data.get(
                "actor_output_name", "root_output"
            ),
            tree_descriptors=self.root_meta_data.get("trees"),
            requested_attributes=self.root_meta_data.get("requested_attributes"),
            skipped_attributes=self.root_meta_data.get("skipped_attributes"),
        )
        if metadata_path is not None:
            self.save_root_metadata(metadata_path)

    def _iter_merge_source_chunks(self, merge_source, step_size="64 MB", library="ak"):
        import uproot

        tree_descriptor = self.get_single_tree_descriptor()
        branch_names = list(tree_descriptor["branches"].keys())
        root_output_path = merge_source["root_output_path"]
        tree_name = tree_descriptor["tree_name"]
        for chunk in uproot.iterate(
            f"{root_output_path}:{tree_name}",
            expressions=branch_names,
            library=library,
            step_size=step_size,
        ):
            yield OrderedDict(
                (branch_name, chunk[branch_name]) for branch_name in branch_names
            )

    def _remap_chunk_identifiers(self, chunk_payload, merge_source, event_id_state):
        remapped_payload = OrderedDict()
        run_id_map = {
            int(local_run_id): int(original_run_id)
            for local_run_id, original_run_id in merge_source.get(
                "run_id_map", {}
            ).items()
        }
        local_run_ids = None
        if "RunID" in chunk_payload:
            # Keep the child-local RunID values in a plain numpy array because we
            # need them twice:
            # 1) to remap RunID itself from child-local to original master run
            #    indices;
            # 2) to detect local run boundaries inside the current streamed
            #    chunk when remapping EventID.
            local_run_ids = np.asarray(chunk_payload["RunID"])

        for branch_name, branch_values in chunk_payload.items():
            if branch_name == "RunID":
                run_ids = np.asarray(branch_values)
                remapped_payload[branch_name] = np.asarray(
                    [run_id_map.get(int(run_id), int(run_id)) for run_id in run_ids],
                    dtype=run_ids.dtype,
                )
            elif branch_name == "EventID":
                event_ids = np.asarray(branch_values)
                if len(event_ids) == 0:
                    remapped_payload[branch_name] = event_ids
                elif local_run_ids is None:
                    # Without RunID we cannot detect local run boundaries, so the
                    # best we can do is append the whole chunk as one event-ID
                    # block. This is acceptable only for outputs that do not
                    # encode per-run identity explicitly.
                    remapped_event_ids = event_ids + event_id_state["next_event_id"]
                    event_id_state["next_event_id"] = int(remapped_event_ids[-1]) + 1
                    remapped_payload[branch_name] = remapped_event_ids
                else:
                    # EventID is only monotonic within one local run. A streamed
                    # chunk may cross local run boundaries, so we detect
                    # contiguous same-RunID blocks inside the chunk and apply one
                    # offset per block rather than one offset for the whole
                    # chunk. This keeps the merge fully streaming while still
                    # respecting the fact that child-local EventID restarts from
                    # zero whenever the child simulation moves to its next local
                    # run.
                    remapped_event_ids = np.empty_like(event_ids)
                    change_indices = np.flatnonzero(np.diff(local_run_ids) != 0) + 1
                    block_starts = np.concatenate(([0], change_indices))
                    block_stops = np.concatenate((change_indices, [len(local_run_ids)]))
                    for start, stop in zip(block_starts, block_stops):
                        block_event_ids = event_ids[start:stop]
                        if len(block_event_ids) == 0:
                            continue
                        # Within one contiguous local-run block, EventID is
                        # already ordered and can be shifted by one constant
                        # offset. The next block starts a fresh local EventID
                        # sequence, so the global offset must be updated at each
                        # boundary.
                        remapped_event_ids[start:stop] = (
                            block_event_ids + event_id_state["next_event_id"]
                        )
                        event_id_state["next_event_id"] = (
                            int(remapped_event_ids[stop - 1]) + 1
                        )
                    remapped_payload[branch_name] = remapped_event_ids
            else:
                remapped_payload[branch_name] = branch_values
        return remapped_payload

    def stream_merge_to_writer(
        self, writer, tree_name=None, step_size="64 MB", event_id_state=None
    ):
        if not self.has_root_meta_data():
            fatal("Cannot stream-merge ROOT output because no ROOT metadata exists.")

        tree_descriptor = self.get_single_tree_descriptor()
        tree_name = tree_name or tree_descriptor["tree_name"]
        if event_id_state is None:
            event_id_state = {"next_event_id": 0}

        for merge_source in self.root_meta_data.get("merge_sources", []):
            for chunk in self._iter_merge_source_chunks(
                merge_source, step_size=step_size, library="ak"
            ):
                if len(next(iter(chunk.values()), [])) == 0:
                    continue
                remapped_chunk = self._remap_chunk_identifiers(
                    chunk, merge_source, event_id_state
                )
                writer.append_chunk(tree_name, remapped_chunk)

    def stream_write_merged_root(
        self,
        output_path,
        metadata_path=None,
        step_size="64 MB",
        writer=None,
        event_id_state=None,
    ):
        if not self.has_root_meta_data():
            fatal(
                "Cannot write streamed merged ROOT output because no ROOT metadata "
                "is available."
            )

        owns_writer = writer is None
        tree_descriptor = self.get_single_tree_descriptor()

        if owns_writer:
            writer = RootMergeFileWriter(output_path)
            writer.open()

        try:
            writer.create_tree(
                tree_descriptor["tree_name"], tree_descriptor["branches"]
            )
            self.stream_merge_to_writer(
                writer,
                tree_name=tree_descriptor["tree_name"],
                step_size=step_size,
                event_id_state=event_id_state,
            )
        finally:
            if owns_writer:
                writer.close()

        self.root_meta_data["root_output_path"] = str(Path(output_path).resolve())
        if metadata_path is not None:
            self.save_root_metadata(metadata_path)


# data items holding images
class ItkImageDataItem(SampleCountingDataItemMixin, DataItem):

    @property
    def image(self):
        return self.data

    @property
    def image_array(self):
        return itk.array_view_from_image(self.image)

    def inplace_merge_with(self, other):
        if other.data is None:
            return self
        if self.data is None:
            self.set_data(copy_itk_image(other.data))
            self.number_of_samples = other.number_of_samples
        else:
            self.__iadd__(other)
            self.number_of_samples += other.number_of_samples
        return self

    def __iadd__(self, other):
        self._assert_data_is_not_none()
        self.set_data(sum_itk_images([self.data, other.data]))
        return self

    def __add__(self, other):
        self._assert_data_is_not_none()
        if isinstance(other, (float, int)):
            return type(self)(data=add_constant_to_itk_image(self.data, other))
        else:
            return type(self)(data=sum_itk_images([self.data, other.data]))

    def __mul__(self, other):
        self._assert_data_is_not_none()
        if isinstance(other, (float, int)):
            return type(self)(data=scale_itk_image(self.data, other))
        else:
            return type(self)(data=multiply_itk_images([self.data, other.data]))

    def __imul__(self, other):
        self._assert_data_is_not_none()
        if isinstance(other, (float, int)):
            self.set_data(scale_itk_image(self.data, other))
        else:
            self.set_data(multiply_itk_images([self.data, other.data]))
        return self

    def __truediv__(self, other):
        self._assert_data_is_not_none()
        if isinstance(other, (float, int)):
            return type(self)(data=scale_itk_image(self.data, 1.0 / other))
        else:
            return type(self)(data=divide_itk_images(self.data, other.data))

    def __itruediv__(self, other):
        self._assert_data_is_not_none()
        if isinstance(other, (float, int)):
            self.set_data(scale_itk_image(self.data, 1.0 / other))
        else:
            self.set_data(divide_itk_images(self.data, other.data))
        return self

    def set_image_properties(self, **properties):
        if not self.data_is_none:
            if "spacing" in properties and properties["spacing"] is not None:
                self.data.SetSpacing(properties["spacing"])
            if "origin" in properties and properties["origin"] is not None:
                self.data.SetOrigin(properties["origin"])
            if "rotation" in properties and properties["rotation"] is not None:
                r = properties["rotation"]
                if self.data.GetImageDimension() == 4:
                    # for 4D image, the rotation is enhanced
                    r = np.pad(
                        r,
                        pad_width=((0, 1), (0, 1)),
                        mode="constant",
                        constant_values=0,
                    )
                    r[3][3] = 1.0
                self.data.SetDirection(r)

    def get_image_properties(self):
        return get_info_from_image(self.data)

    def copy_image_properties(self, other_image):
        self.data.CopyInformation(other_image)

    def set_array_to_image(self, arr):
        image = itk_image_from_array(arr)
        image.SetOrigin(self.image.GetOrigin())
        image.SetSpacing(self.image.GetSpacing())
        image.SetDirection(self.image.GetDirection())
        self.data = image

    def create_empty_image(
        self,
        size,
        spacing,
        origin=None,
        pixel_type="float",
        allocate=True,
        fill_value=0,
    ):
        self.set_data(
            create_3d_image(size, spacing, origin, pixel_type, allocate, fill_value)
        )

    def write(self, path):
        write_itk_image(self.data, ensure_filename_is_str(path))
        metadata_path = _get_sample_count_metadata_path(path)
        with open(metadata_path, "w") as metadata_file:
            json.dump({"number_of_samples": int(self.number_of_samples)}, metadata_file)

    def load(self, path, **kwargs):
        self.set_data(itk.imread(str(path)))
        metadata_path = _get_sample_count_metadata_path(path)
        if metadata_path.exists():
            with open(metadata_path, "r") as metadata_file:
                metadata = json.load(metadata_file)
            try:
                self.number_of_samples = int(metadata["number_of_samples"])
            except (KeyError, TypeError, ValueError):
                warning(
                    f"Could not restore number_of_samples from metadata file "
                    f"'{metadata_path}'. Falling back to the default value "
                    f"{self.number_of_samples}."
                )


class MeanItkImageDataItem(MeanValueDataItemMixin, ItkImageDataItem):
    """This class represents an ITK image which is meant to hold mean values per voxel.
    The class MeanValueDataItemMixin therefore overloads the merge_with and inplace_merge_with methods.
    """


class DataContainer:
    """Common base class for all containers. Nothing implemented here for now."""

    def __init__(self, belongs_to, *args, **kwargs):
        self.belongs_to = belongs_to

    def __copy__(self):
        return type(self)(self.belongs_to)


class DataDictionary(DataContainer):

    def __init__(self, initial_dict, *args, encoder="json", **kwargs):
        self.data = dict([(k, v) for k, v in initial_dict.items()])
        available_encoders = ("json",)
        if encoder in available_encoders:
            self.encoder = encoder
        else:
            fatal(f"Invalid encoder. Available encoders are: {available_encoders}")

    def write(self, path):
        if self.encoder == "json":
            with open(path, "w") as f:
                json.dump(self.data, f, indent=4)


class DataItemContainer(DataContainer):
    """This is a base class. Inherit from it to implement specific containers."""

    # No data item classes specified in the base class.
    # Derived classes must specify this at the class level
    _data_item_classes = ()

    # Primary item identifiers correspond to persisted data items held in
    # ``self.data``. Derived item identifiers refer to computed views such as
    # variance or quotient that are exposed as properties on the container.
    #
    # Derived classes should define these explicitly so the public item surface
    # is visible at the container level instead of being inferred implicitly.
    #
    # Contract:
    # - set ``primary_item_identifiers`` to a non-empty tuple/list for concrete
    #   containers with persisted items
    # - or explicitly set it to ``None`` when a container intentionally exposes
    #   no primary items
    # Inherited values from a base container are valid and intentional.
    primary_item_identifiers = None
    derived_item_identifiers = ()
    _derived_data_item_descriptors = {}

    def __init__(self, *args, data=None, **kwargs):
        super().__init__(*args, **kwargs)

        # create the instances of the data item classes
        # and populate them with data if provided
        self.data = [dic(data=None) for dic in self._data_item_classes]
        for data_item in self.data:
            if data_item is not None:
                data_item.set_owner_container(self)
        if data is not None:
            self.set_data(*data)

    def __copy__(self):
        obj = super().__copy__()
        obj.set_data(*self.data)
        return obj

    @classmethod
    def get_primary_item_identifiers(cls):
        if cls.primary_item_identifiers is None:
            return []
        if len(cls.primary_item_identifiers) == 0:
            raise GateImplementationError(
                f"Data item container class {cls.__name__} must define "
                f"'primary_item_identifiers' explicitly as a non-empty "
                f"sequence or None."
            )
        return list(cls.primary_item_identifiers)

    @classmethod
    def get_derived_item_identifiers(cls):
        return list(getattr(cls, "derived_item_identifiers", ()))

    @classmethod
    def get_item_identifiers(cls):
        item_identifiers = (
            cls.get_primary_item_identifiers() + cls.get_derived_item_identifiers()
        )
        if len(item_identifiers) != len(set(item_identifiers)):
            raise GateImplementationError(
                f"Data item container class {cls.__name__} declares duplicate "
                f"item identifiers: {item_identifiers}"
            )
        return item_identifiers

    @classmethod
    def get_primary_item_identifiers_required_by_items(cls, item_identifiers):
        """Map requested items to the primary items needed to reconstruct them."""
        requested_identifiers = {
            cls.normalize_item_identifier(item_identifier)
            for item_identifier in item_identifiers
        }
        required_primary_identifiers = set()
        for item_identifier in requested_identifiers:
            if item_identifier in cls.get_primary_item_identifiers():
                required_primary_identifiers.add(item_identifier)
            else:
                descriptor = cls._derived_data_item_descriptors.get(item_identifier)
                if descriptor is not None:
                    required_primary_identifiers.update(descriptor["depends_on"])
        return [
            item_identifier
            for item_identifier in cls.get_primary_item_identifiers()
            if item_identifier in required_primary_identifiers
        ]

    @classmethod
    def validate_item_identifier(cls, item):
        cls.normalize_item_identifier(item)

    @classmethod
    def normalize_item_identifier(cls, item):
        for declared_identifier in cls.get_item_identifiers():
            if item == declared_identifier or str(item) == str(declared_identifier):
                return declared_identifier
        raise GateImplementationError(
            f"Unknown data item identifier {item!r} for container class "
            f"{cls.__name__}. Known identifiers are {cls.get_item_identifiers()}."
        )

    def iter_primary_data_items(self):
        for item_identifier in self.get_primary_item_identifiers():
            yield item_identifier, self.get_data_item_object(item_identifier)

    def iter_primary_data_item_objects(self):
        for _, data_item in self.iter_primary_data_items():
            yield data_item

    def iter_all_data_items(self):
        for item_identifier in self.get_item_identifiers():
            yield item_identifier, self.get_data_item_object(item_identifier)

    def iter_all_data_item_objects(self):
        for _, data_item in self.iter_all_data_items():
            yield data_item

    def load_item(self, item="all", path=None, **kwargs):
        if item == "all":
            if path is None:
                fatal(
                    "DataItemContainer.load_item(item='all') requires 'path' to be "
                    "a dictionary mapping item identifiers to file paths."
                )
            try:
                path_items = path.items()
            except AttributeError:
                fatal(
                    "DataItemContainer.load_item(item='all') requires 'path' to be "
                    "a dictionary-like object mapping item identifiers to file paths."
                )
            for item_identifier, item_path in path_items:
                self.load_item(item=item_identifier, path=item_path, **kwargs)
            return

        data_item = self.get_data_item_object(item)
        if data_item is None:
            fatal(f"No data item found for item {item}.")
        data_item.load(path, **kwargs)

    def clear_item(self, item=0):
        data_item = self.get_data_item_object(item)
        if data_item is not None:
            data_item.close_data()

    def clear_items(self, item="all"):
        if item == "all":
            items = self.get_item_identifiers()
        elif isinstance(item, (list, tuple)):
            items = [self.normalize_item_identifier(i) for i in item]
        else:
            items = [self.normalize_item_identifier(item)]
        for item_identifier in items:
            self.clear_item(item_identifier)

    @classmethod
    def build_default_data_item_config(cls):
        """Build neutral actor-output config entries for all items in this container."""

        default_data_item_config = {}
        for item_identifier in cls.get_item_identifiers():
            if isinstance(item_identifier, int):
                suffix = f"item{item_identifier}"
            else:
                suffix = item_identifier
            default_data_item_config[item_identifier] = {
                "output_filename": "auto",
                "write_to_disk": True,
                "active": False,
                "suffix": suffix,
            }

        # Single-output containers are the common case. Keep their filenames
        # clean and make the only item active by default.
        if len(default_data_item_config) == 1:
            only_item_config = next(iter(default_data_item_config.values()))
            only_item_config["suffix"] = None
            only_item_config["active"] = True

        return default_data_item_config

    # the actual write config needs to be fetched from the actor output instance
    # which handles this data item container
    @property
    def data_item_config(self):
        try:
            return self.belongs_to.data_item_config
        except AttributeError:
            raise GateImplementationError("belongs_to unknown")

    @property
    def _tuple_length(self):
        return len(self._data_item_classes)

    @property
    def meta_data(self):
        if self._tuple_length > 1:
            return [d.meta_data for d in self.data]
        else:
            return self.data[0].meta_data

    @meta_data.setter
    def meta_data(self, meta_data):
        for d in self.data:
            d.meta_data = meta_data

    def update_meta_data(self, meta_data):
        for d in self.data:
            if d is not None:
                d.meta_data.update(meta_data)

    def set_number_of_samples(self, number_of_samples, item="all"):
        if item == "all":
            item_identifiers = self.get_primary_item_identifiers()
        elif isinstance(item, (list, tuple)):
            item_identifiers = [self.normalize_item_identifier(i) for i in item]
        else:
            item_identifiers = [self.normalize_item_identifier(item)]

        for item_identifier in item_identifiers:
            data_item = self.get_data_item_object(item_identifier)
            if data_item is None:
                continue
            if not hasattr(data_item, "number_of_samples"):
                raise GateImplementationError(
                    f"Data item {item_identifier!r} of container class "
                    f"{type(self).__name__} does not support sample counting."
                )
            data_item.number_of_samples = number_of_samples

    def set_data(self, *data, item=None):
        # data might be already contained in the correct container class,
        # or intended to be the input to the container class
        if item is not None:
            if isinstance(item, int):
                item = [item]
            else:
                item = list(item)
            if len(data) != len(item):
                fatal(
                    f"Inconsistent input to set_data method: "
                    f"{len(data)} data items provided, "
                    f"but {len(item)} items specified in the 'item' keyword argument. "
                )
        else:
            item = [i for i in range(len(data))]

        if len(item) > 0:
            current_length = len(self.data)
            if any(not isinstance(i, int) for i in item):
                fatal(
                    f"DataItemContainer.set_data() only supports integer indices "
                    f"for explicit item injection, but received items {item}. "
                )
            if item != sorted(item):
                fatal(
                    f"DataItemContainer.set_data() only supports ordered item "
                    f"injection, but received items {item}. "
                )
            if len(set(item)) != len(item):
                fatal(
                    f"DataItemContainer.set_data() received duplicate item "
                    f"indices: {item}. "
                )
            if item[0] > current_length:
                fatal(
                    f"DataItemContainer.set_data() does not support sparse "
                    f"positional injection with gaps. "
                    f"Current container length is {current_length}, but the "
                    f"smallest requested item index is {item[0]}. "
                )
            for previous_item, current_item in zip(item, item[1:]):
                if current_item != previous_item + 1:
                    fatal(
                        f"DataItemContainer.set_data() only supports ordered "
                        f"consecutive positional injection, but received items "
                        f"{item}. "
                    )

        processed_data = list(self.data)
        for i, d in zip(item, data):
            c = self._data_item_classes[i]
            if i > len(processed_data):
                fatal(
                    f"DataItemContainer.set_data() only supports appending items "
                    f"in consecutive positional order. Current processed length "
                    f"is {len(processed_data)}, but item index {i} was requested. "
                )
            if i == len(processed_data):
                processed_data.append(None)
            if isinstance(d, c):
                processed_data[i] = d
            else:
                processed_data[i] = c(data=d)
            if processed_data[i] is not None:
                processed_data[i].set_owner_container(self)
        self.data = processed_data

    def get_data_item_object(self, item=0):
        identifier = self.normalize_item_identifier(item)
        if isinstance(identifier, int):
            try:
                return self.data[identifier]
            except IndexError:
                return None
        return getattr(self, str(identifier), None)

    def get_data(self, item=0):
        identifier = self.normalize_item_identifier(item)
        if isinstance(identifier, int):
            try:
                return self.data[identifier].data
            except IndexError:
                pass
        else:
            try:
                return getattr(self, identifier).data
            except AttributeError:
                pass
        fatal(f"No data found for item {item}. ")

    @property
    def data_is_none(self):
        return any([d is None or d.data_is_none for d in self.data])

    def _assert_data_is_not_none(self):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )

    def propagate_operator(self, other, operator):
        self._assert_data_is_not_none()
        if isinstance(other, (float, int)):
            new_data = [
                getattr(self.data[i], operator)(other)
                for i in range(self._tuple_length)
            ]
        else:
            new_data = [
                getattr(self.data[i], operator)(other.data[i])
                for i in range(self._tuple_length)
            ]
        return type(self)(self._data_item_classes, data=new_data)

    def propagate_operator_inplace(self, other, operator):
        self._assert_data_is_not_none()
        if isinstance(other, (float, int)):
            for i in range(self._tuple_length):
                getattr(self.data[i], operator)(other)
        else:
            for i in range(self._tuple_length):
                getattr(self.data[i], operator)(other.data[i])
        return self

    def __iadd__(self, other):
        return self.propagate_operator_inplace(other, "__iadd__")

    def __add__(self, other):
        return self.propagate_operator(other, "__add__")

    def __imul__(self, other):
        return self.propagate_operator_inplace(other, "__imul__")

    def __mul__(self, other):
        return self.propagate_operator(other, "__mul__")

    def __itruediv__(self, other):
        return self.propagate_operator_inplace(other, "__itruediv__")

    def __truediv__(self, other):
        return self.propagate_operator(other, "__truediv__")

    def inplace_merge_with(self, other):
        for i in range(self._tuple_length):
            # can only apply merge of both items exist (and contain data)
            if self.data[i] is not None and other.data[i] is not None:
                self.data[i].inplace_merge_with(other.data[i])
            else:
                # the case of both item None is acceptable
                # because the component not be activated in the actor, e.g. edep uncertainty,
                # but it should not occur that one item is None and the other is not.
                if (self.data[i] is None) is not (other.data[i] is None):
                    s_not = {True: "", False: "not"}
                    fatal(
                        "Cannot apply inplace merge data to container "
                        "with unset (None) data items. "
                        f"In this case, the inplace item {i} is {s_not[self.data[i] is None]} None, "
                        f"and the other item {i} is {s_not[other.data[i] is None]} None. "
                        f"This is likely an implementation error in GATE. "
                    )
        return self

    def merge_with(self, other):
        data = []
        for i in range(self._tuple_length):
            if (
                self.data[i] is not None
                and other.data[i] is not None
                and self.data[i].data is not None
                and other.data[i].data is not None
            ):
                data.append(self.data[i].merge_with(other.data[i]))
            else:
                # FIXME: we need a consistency check here
                data.append(None)

        return type(self)(
            self._data_item_classes,
            data=data,
        )

    def write(self, path, item, **kwargs):
        data_item = self.get_data_item_object(item)
        if data_item is not None:
            data_item.write(path, **kwargs)
        else:
            warning(f"Cannot write item {item} because it does not exist (=None).")

    def __getattr__(self, item):
        if item in ("data", "__setstate__", "__getstate__"):
            raise AttributeError(f"No such attribute '{item}'")
        _raise_pre_interface_convenience_deprecation(type(self).__name__, item)


class SingleArray(DataItemContainer):

    _data_item_classes = (ArrayDataItem,)
    primary_item_identifiers = (0,)

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__(*args, **kwargs)


class DoubleArray(DataItemContainer):

    _data_item_classes = (ArrayDataItem, ArrayDataItem)
    primary_item_identifiers = (0, 1)

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__(*args, **kwargs)


class ImageDataItemContainerMixin:
    """This class should be mixed in via inheritance when
    implementing specific image item container class.

    It provides convenience shortcuts to the image-specific functionality of the data items
    handled by the container.

    The pattern is:
    - getters and getter properties shortcut to item 0
    - setting operations are propagated to all items.
    """

    @property
    def _image_data_items(self):
        return [d for d in self.data if d is not None]

    def _get_image_data_items(self, item="all"):
        if item == "all":
            return self._image_data_items
        data_item = self.get_data_item_object(item)
        if data_item is None:
            fatal(f"No image data item found for item {item}.")
        return [data_item]

    @property
    def _primary_image_data_item(self):
        try:
            return self.data[0]
        except (AttributeError, IndexError):
            fatal("No primary image data item found in this container.")

    @property
    def image(self):
        return self._primary_image_data_item.image

    @property
    def image_array(self):
        return self._primary_image_data_item.image_array

    def get_image_properties(self, item=0):
        return self.get_data_item_object(item).get_image_properties()

    def set_image_properties(self, item="all", **properties):
        for image_data_item in self._get_image_data_items(item=item):
            image_data_item.set_image_properties(**properties)

    def copy_image_properties(self, other_image, item="all"):
        for image_data_item in self._get_image_data_items(item=item):
            image_data_item.copy_image_properties(other_image)

    def set_array_to_image(self, arr, item="all"):
        for image_data_item in self._get_image_data_items(item=item):
            image_data_item.set_array_to_image(arr)

    def create_empty_image(
        self,
        size,
        spacing,
        origin=None,
        pixel_type="float",
        allocate=True,
        fill_value=0,
        item="all",
    ):
        # Setter-style operations on image containers default to item="all" so
        # multi-image outputs keep their persisted items structurally aligned.
        for image_data_item in self._get_image_data_items(item=item):
            image_data_item.create_empty_image(
                size,
                spacing,
                origin=origin,
                pixel_type=pixel_type,
                allocate=allocate,
                fill_value=fill_value,
            )


class SingleItkImage(ImageDataItemContainerMixin, DataItemContainer):

    _data_item_classes = (ItkImageDataItem,)
    primary_item_identifiers = (0,)


class SingleMeanItkImage(ImageDataItemContainerMixin, DataItemContainer):

    _data_item_classes = (MeanItkImageDataItem,)
    primary_item_identifiers = (0,)


class SingleItkImageWithVariance(ImageDataItemContainerMixin, DataItemContainer):

    _data_item_classes = (
        ItkImageDataItem,
        ItkImageDataItem,
    )
    primary_item_identifiers = (0, 1)

    # # Only the linear quantity is active by default
    # # the uncertainty quantity has write_to_disk=True by default so whenever it is activated,
    # # the results will be written to disk (probably the expected default behavior in most cases)
    # default_data_item_config = Box(
    #     {
    #         0: Box({"output_filename": "auto", "write_to_disk": True, "active": True}),
    #         1: Box(
    #             {"output_filename": "auto", "write_to_disk": False, "active": False}
    #         ),
    #         "variance": Box(
    #             {"output_filename": "auto", "write_to_disk": False, "active": False}
    #         ),
    #         "std": Box(
    #             {"output_filename": "auto", "write_to_disk": False, "active": False}
    #         ),
    #         "uncertainty": Box(
    #             {"output_filename": "auto", "write_to_disk": True, "active": False}
    #         ),
    #     }
    # )
    def get_variance_or_uncertainty(self, which_quantity):
        try:
            number_of_samples = self.data[0].number_of_samples
            value_array = np.asarray(self.data[0].data)
            if not number_of_samples > 1:
                warning(
                    "You try to compute statistical errors with only one or zero event! "
                    "The uncertainty value for all voxels has been fixed at 1"
                )
                output_arr = np.ones_like(value_array)
            elif self.data[1] is None or self.data[1].data is None:
                warning(
                    "This data item does not contain squared values so no variance can be calculated. "
                    "The variance will be set to 0 everywhere. "
                )
                output_arr = np.zeros_like(value_array)
            else:
                squared_value_array = np.asarray(self.data[1].data)
                output_arr = calculate_variance(
                    value_array, squared_value_array, number_of_samples
                )
                if which_quantity in (
                    "std",
                    "uncertainty",
                ):
                    output_arr = np.sqrt(output_arr)
                if which_quantity in ("uncertainty",):
                    output_arr = np.divide(
                        output_arr,
                        value_array / number_of_samples,
                        out=np.zeros_like(output_arr),
                        where=value_array != 0,
                    )
            output_image = itk_image_from_array(output_arr)
            output_image.CopyInformation(self.data[0].data)
        except AttributeError as e:
            fatal(str(e))
        return self._data_item_classes[0](data=output_image)

    @derived_data_item(depends_on=(0, 1))
    def variance(self):
        return self.get_variance_or_uncertainty("variance")

    @derived_data_item(depends_on=(0, 1))
    def std(self):
        return self.get_variance_or_uncertainty("std")

    @derived_data_item(depends_on=(0, 1))
    def uncertainty(self):
        return self.get_variance_or_uncertainty("uncertainty")


class QuotientItkImage(ImageDataItemContainerMixin, DataItemContainer):

    _data_item_classes = (
        ItkImageDataItem,
        ItkImageDataItem,
    )
    primary_item_identifiers = (0, 1)

    # # Specify which items should be written to disk and how
    # # Important: define this at the class level, NOT in the __init__ method
    # default_data_item_config = Box(
    #     {
    #         0: Box({"output_filename": "auto", "write_to_disk": True, "active": True}),
    #         1: Box({"output_filename": "auto", "write_to_disk": True, "active": True}),
    #         "quotient": Box(
    #             {"output_filename": "auto", "write_to_disk": True, "active": True}
    #         ),
    #     }
    # )

    @derived_data_item(depends_on=(0, 1))
    def quotient(self):
        return self.data[0] / self.data[1]


class QuotientMeanItkImage(QuotientItkImage):

    _data_item_classes = (
        MeanItkImageDataItem,
        MeanItkImageDataItem,
    )


class SingleTimeCountSeries(DataItemContainer):

    _data_item_classes = (TimeCountSeriesDataItem,)
    primary_item_identifiers = (0,)


class SingleRootTree(DataItemContainer):

    _data_item_classes = (RootDataItem,)
    primary_item_identifiers = (0,)


class StatisticsItemContainer(DataItemContainer):

    _data_item_classes = (StatisticsDataItem,)
    primary_item_identifiers = (0,)

    @property
    def _stats_item(self):
        try:
            return self.data[0]
        except (AttributeError, IndexError):
            raise AttributeError("Statistics item container has no primary data item.")

    @property
    def _known_stats_entry_names(self):
        return self._data_item_classes[0].get_known_entry_names()

    def __getattr__(self, item):
        if item in ("data", "belongs_to", "__setstate__", "__getstate__"):
            raise AttributeError(f"No such attribute '{item}'")
        if item in self._known_stats_entry_names:
            return getattr(self._stats_item, item)
        return super().__getattr__(item)

    def __setattr__(self, item, value):
        if item in ("data", "belongs_to"):
            object.__setattr__(self, item, value)
            return
        if item in self._known_stats_entry_names:
            setattr(self._stats_item.data, item, value)
            return
        if item not in ("__setstate__", "__getstate__"):
            _raise_pre_interface_convenience_deprecation(
                type(self).__name__, f"setattr({item})"
            )
        object.__setattr__(self, item, value)


def merge_data(list_of_data):
    merged_data = type(list_of_data[0])(list_of_data[0].belongs_to)
    for d in list_of_data:
        merged_data.inplace_merge_with(d)
    return merged_data


available_data_container_classes = {
    "SingleItkImage": SingleItkImage,
    "SingleMeanItkImage": SingleMeanItkImage,
    "QuotientMeanItkImage": QuotientMeanItkImage,
    "SingleArray": SingleArray,
    "DoubleArray": DoubleArray,
    "SingleItkImageWithVariance": SingleItkImageWithVariance,
    "SingleRootTree": SingleRootTree,
}


def _get_derived_data_item_descriptor_from_attribute(attribute):
    if not isinstance(attribute, property):
        return None
    getter = attribute.fget
    if getter is None or not getattr(getter, "_gate_is_derived_data_item", False):
        return None
    return {
        "name": getter._gate_derived_item_name,
        "depends_on": tuple(getter._gate_depends_on),
        "property_name": getter.__name__,
    }


def _process_data_item_container_class(cls):
    """Collect inherited derived-data-item metadata for one container class."""

    derived_data_item_descriptors = OrderedDict()
    manual_derived_item_identifiers = []

    for candidate_class in reversed(cls.mro()):
        if not issubclass(candidate_class, DataItemContainer):
            continue
        if candidate_class is DataItemContainer:
            continue

        decorated_descriptors_in_this_class = [
            descriptor
            for descriptor in (
                _get_derived_data_item_descriptor_from_attribute(attribute)
                for attribute in candidate_class.__dict__.values()
            )
            if descriptor is not None
        ]

        if (
            "derived_item_identifiers" in candidate_class.__dict__
            and len(decorated_descriptors_in_this_class) == 0
            and len(candidate_class.__dict__.get("_derived_data_item_descriptors", {}))
            == 0
        ):
            declared = list(candidate_class.__dict__["derived_item_identifiers"])
            if len(declared) > 0:
                manual_derived_item_identifiers.extend(declared)

        for descriptor in decorated_descriptors_in_this_class:
            derived_data_item_descriptors[descriptor["name"]] = descriptor

    if (
        len(manual_derived_item_identifiers) > 0
        and len(derived_data_item_descriptors) > 0
    ):
        raise GateImplementationError(
            f"Data item container class {cls.__name__} mixes manual "
            f"'derived_item_identifiers' with @derived_data_item declarations. "
            f"Use one source of truth only."
        )

    if len(derived_data_item_descriptors) > 0:
        primary_item_identifiers = set(cls.get_primary_item_identifiers())
        for descriptor in derived_data_item_descriptors.values():
            invalid_dependencies = [
                item_identifier
                for item_identifier in descriptor["depends_on"]
                if item_identifier not in primary_item_identifiers
            ]
            if len(invalid_dependencies) > 0:
                raise GateImplementationError(
                    f"Derived data item '{descriptor['name']}' of container class "
                    f"{cls.__name__} depends on invalid primary item identifiers "
                    f"{invalid_dependencies}. Valid primary item identifiers are "
                    f"{cls.get_primary_item_identifiers()}."
                )

    cls._derived_data_item_descriptors = dict(derived_data_item_descriptors)
    cls.derived_item_identifiers = tuple(derived_data_item_descriptors.keys())
    return cls


def _process_data_item_container_classes_in_module():
    """Finalize derived-data-item metadata after all container classes exist."""

    for candidate in globals().values():
        if not isinstance(candidate, type):
            continue
        if not issubclass(candidate, DataItemContainer):
            continue
        if candidate is DataItemContainer:
            continue
        _process_data_item_container_class(candidate)


_process_data_item_container_classes_in_module()
