import numpy as np
from pathlib import Path

from ..base import GateObject
from ..image import (
    write_itk_image,
    update_image_py_to_cpp,
    create_3d_image,
    get_py_image_from_cpp_image,
    sum_itk_images,
    divide_itk_images,
)
from ..utility import ensure_filename_is_str, insert_suffix_before_extension
from ..exception import warning, fatal


class SingleDataItem:

    def __new__(cls, *args, **kwargs):
        cls._tuple_length = 1
        return super(SingleDataItem, cls).__new__(cls)

    def __init__(self, *args, data=None, **kwargs):
        self.set_data(data)

    def set_data(self, data):
        self.data = data

    @property
    def data_is_none(self):
        return self.data is None

    def get_output_path_to_item(self, actor_output_path, item):
        """Dummy method to be called from ActorOutput"""
        return actor_output_path

    def __add__(self, other):
        return NotImplemented

    def __iadd__(self, other):
        return NotImplemented

    def __truediv__(self, other):
        return NotImplemented

    def __getattr__(self, item):
        # check if any of the data items has this attribute
        if hasattr(self.data, item) and callable(getattr(self.data, item)):

            def hand_down(*args, **kwargs):
                getattr(self.data, item)(*args, **kwargs)

            return hand_down
        else:
            raise AttributeError(f"No such attribute '{item}'")

    def write(self, *args, **kwargs):
        raise NotImplementedError(f"This is the base class. ")


class MultiDataItem:

    def __new__(cls, tuple_length, *args, **kwargs):
        cls._tuple_length = tuple_length
        return super(MultiDataItem, cls).__new__(cls)

    def __init__(self, data_item_classes, *args, data=None, **kwargs):
        if len(data_item_classes) != self._tuple_length:
            fatal(
                f"The number of data item classes does not match the number of data items managed by this class. "
                f"Received {len(data_item_classes)} classes, but need {self._tuple_length}."
            )
        for dic in data_item_classes:
            if dic not in list(available_data_item_classes.values()):
                fatal(
                    f"Illegal data item class {dic}. "
                    f"Available classes are {list(available_data_item_classes.values())}."
                )
        self.data_item_classes = data_item_classes
        if data is None:
            self.set_data(*([None] * self._tuple_length))
        else:
            self.set_data(*data)
        self.custom_output_config = {}

    def set_data(self, *data):
        # data might be already contained in the correct container class,
        # or intended to be the input to the container class
        processed_data = []
        for d, c in zip(data, self.data_item_classes):
            if isinstance(d, c):
                processed_data.append(d)
            else:
                processed_data.append(c(data=d))
        self.data = processed_data

    @property
    def data_is_none(self):
        return any([d is None for d in self.data])

    def _assert_data_is_not_none(self):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )

    def __iadd__(self, other):
        self._assert_data_is_not_none()
        for i in range(self._tuple_length):
            self.data[i].__iadd__(other.data[i])
        return self

    def __add__(self, other):
        self._assert_data_is_not_none()
        return type(self)(
            self.data_item_classes,
            data=[
                self.data[i].__trueadd__(other.data[i])
                for i in range(self._tuple_length)
            ],
        )

    def __itruediv__(self, other):
        self._assert_data_is_not_none()
        for i in range(self._tuple_length):
            self.data[i].__itruediv__(other.data[i])
        return self

    def __truediv__(self, other):
        self._assert_data_is_not_none()
        return type(self)(
            self.data_item_classes,
            data=[
                self.data[i].__truediv__(other.data[i])
                for i in range(self._tuple_length)
            ],
        )

    def write(self, path):
        for k, v in self.get_output_config().items():
            full_path = insert_suffix_before_extension(path, v)
            try:
                i = int(k)
                try:
                    self.data[i].write(full_path)
                except IndexError:
                    warning(f"No data for item number {i}. Cannot write this output")
            except TypeError:
                getattr(self, str(k)).write(full_path)

    def get_output_path_to_item(self, actor_output_path, item):
        """This method is intended to be called from an ActorOutput object which provides the path.
        It returns the amended path to the specific item, e.g. the numerator or denominator in a QuotientDataItem.
        Do not override this method.
        """
        return insert_suffix_before_extension(
            actor_output_path, self.get_output_config()[item]
        )

    def get_output_config(self):
        output_config = dict([(k, v) for k, v in self.custom_output_config.items()])
        for i, d in enumerate(self.data):
            if i not in output_config:
                output_config[i] = f"item_{i}"
        return output_config

    def __getattr__(self, item):
        # check if any of the data items has this attribute
        methods_in_data = []
        for d in self.data:
            if hasattr(d, item) and callable(getattr(d, item)):
                methods_in_data.append(getattr(d, item))
        if len(methods_in_data) > 0:

            def hand_down(*args, **kwargs):
                for m in methods_in_data:
                    m(*args, **kwargs)

            return hand_down
        else:
            raise AttributeError(f"No such attribute '{item}'")


class DoubleDataItem(MultiDataItem):

    def __new__(cls, *args, **kwargs):
        return super(DoubleDataItem, cls).__new__(cls, 2, *args, **kwargs)


class QuotientDataItem(DoubleDataItem):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_output_config.update(
            {0: "numerator", 1: "denominator", "quotient": "quotient"}
        )

    @property
    def numerator(self):
        return self.data[0]

    @property
    def denominator(self):
        return self.data[1]

    @property
    def quotient(self):
        return self.numerator / self.denominator


class SingleArrayDataItem(SingleDataItem):

    def set_data(self, data):
        super().set_data(np.asarray(data))

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

    def write(self, path):
        np.savetxt(path, self.data)


class DoubleArrayDataItem(DoubleDataItem):

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__((SingleArrayDataItem, SingleArrayDataItem), *args, **kwargs)


class SingleItkImageDataItem(SingleDataItem):

    @property
    def image(self):
        return self.data

    def __iadd__(self, other):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )
        self.set_data(sum_itk_images([self.data, other.data]))
        return self

    def __add__(self, other):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )
        return type(self)(data=sum_itk_images([self.data, other.data]))

    def __truediv__(self, other):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )
        return type(self)(data=divide_itk_images(self.data, other.data))

    def __itruediv__(self, other):
        if self.data_is_none:
            raise ValueError(
                "This data item does not contain any data yet. "
                "Use set_data() before applying any operations. "
            )
        self.set_data(divide_itk_images(self.data, other.data))
        return self

    def set_image_properties(self, spacing=None, origin=None):
        if not self.data_is_none:
            if spacing is not None:
                self.data.SetSpacing(spacing)
            if origin is not None:
                self.data.SetOrigin(origin)

    def create_empty_image(
        self, size, spacing, pixel_type="float", allocate=True, fill_value=0
    ):
        self.set_data(create_3d_image(size, spacing, pixel_type, allocate, fill_value))

    def write(self, path):
        write_itk_image(self.data, ensure_filename_is_str(path))


class QuotientItkImageDataItem(QuotientDataItem):

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__(
            (SingleItkImageDataItem, SingleItkImageDataItem), *args, **kwargs
        )


available_data_item_classes = {
    "SingleItkImage": SingleItkImageDataItem,
    "QuotientImageDataItem": QuotientItkImageDataItem,
    "SingleArrayDataItem": SingleArrayDataItem,
    "DoubleArrayDataItem": DoubleArrayDataItem,
}


def _setter_hook_belongs_to(self, belongs_to):
    if belongs_to is None:
        fatal("The belongs_to attribute of an ActorOutput cannot be None.")
    try:
        belongs_to_name = belongs_to.name
    except AttributeError:
        belongs_to_name = belongs_to
    return belongs_to_name


def _setter_hook_path(self, path):
    return Path(path)


class ActorOutput(GateObject):
    user_info_defaults = {
        "belongs_to": (
            None,
            {
                "doc": "Name of the actor to which this output belongs.",
                "setter_hook": _setter_hook_belongs_to,
                "required": True,
            },
        ),
        "output_filename": (
            None,
            {
                "doc": "Filename for the data represented by this actor output. "
                "Relative paths and filenames are taken "
                "relative to the global simulation output folder "
                "set via the Simulation.output_path option. ",
            },
        ),
        "write_to_disk": (
            True,
            {
                "doc": "Should the data be written to disk?",
            },
        ),
        "keep_data_in_memory": (
            True,
            {
                "doc": "Should the data be kept in memory after the end of the simulation? "
                "Otherwise, it is only stored on disk and needs to be re-loaded manually. "
                "Careful: Large data structures like a phase space need a lot of memory.",
            },
        ),
        "keep_data_per_run": (
            False,
            {
                "doc": "In case the simulation has multiple runs, should separate results per run be kept?"
            },
        ),
        "auto_merge": (
            True,
            {
                "doc": "In case the simulation has multiple runs, should results from separate runs be merged?"
            },
        ),
        "data_item_class": (
            None,
            {"doc": "FIXME"},
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_suffix = ""

        if self.output_filename is None:
            self.output_filename = f"output_{self.name}_from_actor_{self.belongs_to_actor.name}.{self.default_suffix}"

        self.data_per_run = {}  # holds the data per run in memory
        self.merged_data = None  # holds the data merged from multiple runs in memory

    # def __contains__(self, item):
    #     return item in self.data_per_run

    def __len__(self):
        return len(self.data_per_run)

    @property
    def data(self):
        if len(self.data_per_run) > 1:
            warning(
                f"You are using the convenience property 'data' to access the data in this actor output. "
                f"This returns you the data from the first run, but the actor output stores "
                f"data from {len(self.data_per_run)} runs. "
                f"To access them, use 'data_per_run[RUN_INDEX]' instead or 'merged_data'. "
            )
        return self.data_per_run[0]

    @property
    def belongs_to_actor(self):
        return self.simulation.actor_manager.get_actor(self.belongs_to)

    def merge_data(self, list_of_data):
        raise NotImplementedError(
            f"Your are calling this method from the base class {type(self).__name__}, "
            f"but it should be implemented in the specific derived class"
        )

    def merge_data_from_runs(self):
        self.merged_data = self.merge_data(list(self.data_per_run.values()))

    def merge_into_merged_data(self, data):
        self.merged_data = self.merge_data([self.merged_data, data])

    def end_of_run(self, run_index):
        if self.keep_data_per_run is False:
            if self.auto_merge is True:
                self.merge_into_merged_data(self.data_per_run[run_index])
            self.data_per_run[run_index] = None

    def end_of_simulation(self):
        if self.auto_merge is True:
            self.merge_data_from_runs()
        if self.keep_data_per_run is False:
            for k in self.data_per_run:
                self.data_per_run[k] = None

    def store_data(self, data, which):
        if isinstance(data, available_data_item_classes[self.data_item_class]):
            data_item = data
        else:
            data_item = available_data_item_classes[self.data_item_class](data=data)
        if which == "merged":
            self.merged_data = data_item
        else:
            try:
                run_index = int(which)  # might be a run_index
                if run_index not in self.data_per_run:
                    self.data_per_run[run_index] = data_item
                else:
                    fatal(
                        f"A data item is already set for run index {run_index}. "
                        f"You can only merge additional data into it. Overwriting is not allowed. "
                    )
            except ValueError:
                fatal(
                    f"Invalid argument 'which' in store_data() method of ActorOutput {self.name}. "
                    f"Allowed values are: 'merged' or a valid run_index. "
                )

    def load_data(self, which):
        raise NotImplementedError(
            f"Your are calling this method from the base class {type(self).__name__}, "
            f"but it should be implemented in the specific derived class"
        )

    def collect_data(self, which, return_identifier=False):
        if which == "merged":
            data = [self.merged_data]
            identifiers = ["merged"]
        elif which == "all_runs":
            data = list(self.data_per_run.values())
            identifiers = list(self.data_per_run.keys())
        elif which == "all":
            data = list(self.data_per_run.values())
            data.append(self.merged_data)
            identifiers = list(self.data_per_run.keys())
            identifiers.append("merged")
        else:
            try:
                ri = int(which)
            except ValueError:
                fatal(f"Invalid argument which in method collect_images(): {which}")
            data = [self.data_per_run[ri]]
            identifiers = [ri]
        if return_identifier is True:
            return data, identifiers
        else:
            return data

    def write_data(self, which):
        if which == "all_runs":
            for i, data in self.data_per_run.items():
                if data is not None:
                    data.write(self.get_output_path(i))
        elif which == "merged":
            self.merged_data.write(self.get_output_path(which))
        elif which == "all":
            self.write_data("all_runs")
            self.write_data("merged")
        else:
            try:
                data = self.data_per_run[which]
            except KeyError:
                fatal(
                    f"Invalid argument 'which' in method write_data(): {which}. "
                    f"Allowed values are 'all', 'all_runs', 'merged', or a valid run_index"
                )
            data.write(self.get_output_path(which))

    def write_data_if_requested(self, *args, **kwargs):
        if self.write_to_disk is True:
            self.write_data(*args, **kwargs)

    def get_output_path(self, which):
        full_data_path = self.simulation.get_output_path(self.output_filename)
        if which == "merged":
            return full_data_path.with_name(
                full_data_path.stem + f"_merged" + full_data_path.suffix
            )
        else:
            try:
                run_index = int(which)
            except ValueError:
                fatal(
                    f"Invalid argument 'which' in get_output_path() method "
                    f"of {type(self).__name__} called {self.name}"
                    f"Valid arguments are a run index (int) or the term 'merged'. "
                )
            return full_data_path.with_name(
                full_data_path.stem + f"_run{run_index:04f}" + full_data_path.suffix
            )

    def get_output_path_for_item(self, which, item):
        output_path = self.get_output_path(which)
        if which == "merged":
            data = self.merged_data
        else:
            try:
                data = self.data_per_run[which]
            except KeyError:
                fatal(
                    f"Invalid argument 'which' in method get_output_path_for_item(): {which}. "
                    f"Allowed values are 'merged' or a valid run_index. "
                )
        return data.get_output_path_to_item(output_path, item)

    def close(self):
        if self.keep_data_in_memory is False:
            self.data_per_run = {}
            self.merged_data = None
        super().close()


class ActorOutputImage(ActorOutput):
    user_info_defaults = {
        "merge_method": (
            "sum",
            {
                "doc": "How should images from runs be merged?",
                "allowed_values": ("sum",),
            },
        ),
        "size": (
            None,
            {
                "doc": "Size of the image in voxels.",
            },
        ),
        "spacing": (
            None,
            {
                "doc": "Spacing of the image.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_suffix = "mhd"

    # override merge_data() method
    def merge_data(self, list_of_data):
        if self.merge_method == "sum":
            merged_data = list_of_data[0]
            for d in list_of_data[1:]:
                merged_data += d
            return merged_data

    def set_image_properties(self, which, **kwargs):
        for image_data in self.collect_data(which):
            if image_data is not None:
                image_data.set_image_properties(**kwargs)

    def create_empty_image(self, run_index, *args, **kwargs):
        self.data_per_run[run_index].create_empty_image(*args, **kwargs)

    def update_to_cpp_image(self, cpp_image, run_index, copy_data=False):
        update_image_py_to_cpp(
            self.data_per_run[run_index], cpp_image, copy_data=copy_data
        )

    def update_from_cpp_image(self, cpp_image, run_index):
        self.data_per_run[run_index] = get_py_image_from_cpp_image(cpp_image)


class ActorOutputRoot(ActorOutput):
    user_info_defaults = {
        "merge_method": (
            "append",
            {
                "doc": "How should images from runs be merged?",
                "allowed_values": ("append",),
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_suffix = "root"

    def merge_data(self, list_of_data):
        if self.merge_method == "append":
            raise NotImplementedError("Appending ROOT files not yet implemented.")


actor_output_classes = {"root": ActorOutputRoot, "image": ActorOutputImage}
