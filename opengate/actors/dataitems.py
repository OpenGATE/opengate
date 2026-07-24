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
import platform
from box import Box

from ..exception import fatal, warning, GateImplementationError
from ..serialization import dump_json
from ..utility import ensure_filename_is_str, calculate_variance
from ..utility import g4_best_unit_tuple, g4_units
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
        if data is not None:
            self.set_data(data)
        self.meta_data = Box({"number_of_samples": 1})
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

    @property
    def number_of_samples(self):
        try:
            return self.meta_data["number_of_samples"]
        except KeyError:
            fatal(
                f"This data item holds a mean value, "
                f"but the meta_data dictionary does not contain any value for 'number_of_samples'."
            )

    @number_of_samples.setter
    def number_of_samples(self, value):
        self.meta_data["number_of_samples"] = int(value)


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


# data items holding images
class ItkImageDataItem(DataItem):

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

    def __init__(self, *args, data=None, **kwargs):
        super().__init__(*args, **kwargs)

        # create the instances of the data item classes
        # and populate them with data if provided
        self.data = [dic(data=None) for dic in self._data_item_classes]
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
        return list(cls.derived_item_identifiers)

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

    def set_data(self, *data, item=None):
        # data might be already contained in the correct container class,
        # or intended to be the input to the container class
        if item is not None:
            if len(data) != len(item):
                fatal(
                    f"Inconsistent input to set_data method: "
                    f"{len(data)} data items provided, "
                    f"but {len(item)} items specified in the 'item' keyword argument. "
                )
        else:
            item = [i for i in range(len(data))]
        processed_data = []
        for i, d in zip(item, data):
            c = self._data_item_classes[i]
            if isinstance(d, c):
                processed_data.append(d)
            else:
                processed_data.append(c(data=d))
        # Fill up the data list with None in case not all data were passed
        # processed_data.extend([None] * (len(self._data_item_classes) - len(data)))
        self.data = processed_data

    def get_data_item_object(self, item):
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
        # FIXME: this generic proxy hides too much of the public API surface of
        # containers. Prefer explicit container-level wrapper properties and
        # methods for intentional forwarding, and keep this fallback only for
        # compatibility until call sites have been migrated.
        # check if any of the data items has this attribute
        # exclude 'data' to avoid infinite recursion
        # exclude '__setstate__' and '__getstate__' to avoid interference with pickling
        if item not in ("data", "__setstate__", "__getstate__"):
            methods_in_data = []
            attributes_in_data = []
            for d in self.data:
                if d is not None and hasattr(d, item):
                    if callable(getattr(d, item)):
                        methods_in_data.append(getattr(d, item))
                    else:
                        attributes_in_data.append(getattr(d, item))
            if len(attributes_in_data) > 0 and len(methods_in_data) > 0:
                fatal(
                    f"Cannot hand down request for attribute to data items "
                    f"because some contain it as a method and other as a property. "
                )
            elif len(attributes_in_data) > 0:
                if len(attributes_in_data) == 1:
                    return attributes_in_data[0]
                else:
                    return attributes_in_data
            elif len(methods_in_data) > 0:

                def hand_down(*args, **kwargs):
                    return_values = []
                    for m in methods_in_data:
                        return_values.append(m(*args, **kwargs))
                    return tuple(return_values)

                return hand_down
            else:
                raise AttributeError(f"No such attribute '{item}'")
        else:
            raise AttributeError(f"No such attribute '{item}'")


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

    @property
    def _image_data_items(self):
        return [d for d in self.data if d is not None]

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

    def get_image_properties(self):
        return tuple(d.get_image_properties() for d in self._image_data_items)

    def set_image_properties(self, **properties):
        for image_data_item in self._image_data_items:
            image_data_item.set_image_properties(**properties)

    def copy_image_properties(self, other_image):
        for image_data_item in self._image_data_items:
            image_data_item.copy_image_properties(other_image)

    def set_array_to_image(self, arr):
        for image_data_item in self._image_data_items:
            image_data_item.set_array_to_image(arr)

    def create_empty_image(
        self,
        size,
        spacing,
        origin=None,
        pixel_type="float",
        allocate=True,
        fill_value=0,
    ):
        # Multi-image containers such as value+squared-value outputs need all
        # persisted image items to be allocated and kept geometrically aligned.
        # The old generic forwarding did this implicitly for every image-backed
        # data item; keep that behavior here explicitly.
        for image_data_item in self._image_data_items:
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
    derived_item_identifiers = ("variance", "std", "uncertainty")

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

    @property
    def variance(self):
        return self.get_variance_or_uncertainty("variance")

    @property
    def std(self):
        return self.get_variance_or_uncertainty("std")

    @property
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

    derived_item_identifiers = ("quotient",)

    @property
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


class StatisticsItemContainer(DataItemContainer):

    _data_item_classes = (StatisticsDataItem,)
    primary_item_identifiers = (0,)

    def __getattr__(self, item):
        if item not in ("data", "belongs_to", "__setstate__", "__getstate__"):
            try:
                return getattr(self.data[0].data, item)
            except (AttributeError, IndexError):
                pass
        return super().__getattr__(item)

    def __setattr__(self, item, value):
        if item in ("data", "belongs_to"):
            object.__setattr__(self, item, value)
            return
        if "data" in self.__dict__ and len(self.data) > 0 and self.data[0].data is not None:
            if hasattr(self.data[0].data, item):
                setattr(self.data[0].data, item, value)
                return
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
}
