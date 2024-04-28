import numpy as np
import json

from ..exception import fatal, warning
from ..utility import insert_suffix_before_extension, ensure_filename_is_str, g4_units
from ..image import (
    sum_itk_images,
    divide_itk_images,
    create_3d_image,
    write_itk_image,
    get_info_from_image,
)


# base classes
class DataItem:

    def __init__(self, *args, data=None, **kwargs):
        self.set_data(data)

    def set_data(self, data):
        self.data = data

    @property
    def data_is_none(self):
        return self.data is None

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


# data items holding arrays
class ArrayDataItem(ArithmeticDataItem):

    def set_data(self, data):
        super().set_data(np.asarray(data))

    def write(self, path):
        np.savetxt(path, self.data)


class ScalarDataItem(ArithmeticDataItem):

    def write(self, *args, **kwargs):
        raise NotImplementedError


# data items holding images
class ItkImageDataItem(DataItem):

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

    def set_image_properties(self, **properties):
        if not self.data_is_none:
            if "spacing" in properties and properties["spacing"] is not None:
                self.data.SetSpacing(properties["spacing"])
            if "origin" in properties and properties["origin"] is not None:
                self.data.SetOrigin(properties["origin"])
            if "rotation" in properties and properties["rotation"] is not None:
                self.data.SetDirection(properties["rotation"])

    def get_image_properties(self):
        return get_info_from_image(self.data)

    def create_empty_image(
        self, size, spacing, pixel_type="float", allocate=True, fill_value=0
    ):
        self.set_data(create_3d_image(size, spacing, pixel_type, allocate, fill_value))

    def write(self, path):
        write_itk_image(self.data, ensure_filename_is_str(path))


class DataContainer:
    """Common base class for all containers. Nothing implemented here for now."""

    pass


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

    def __init__(self, data_item_classes, *args, data=None, **kwargs):
        self._tuple_length = len(data_item_classes)
        for dic in data_item_classes:
            if DataItem not in dic.mro():
                fatal(f"Illegal data item class {dic}. ")
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

    def get_data(self, item=None):
        if item is None:
            if self._tuple_length > 1:
                return tuple([d.data for d in self.data])
            else:
                return self.data[0].data
        else:
            try:
                item_index = int(item)
                try:
                    return self.data[item_index].data
                except IndexError:
                    fatal(f"No data for {item} found. ")
            except ValueError:
                fatal(f"Illegal keyword argument 'item' {item}.")

    @property
    def data_is_none(self):
        return any([d is None or d.data_is_none() for d in self.data])

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
        for k, v in self._get_output_config().items():
            full_path = insert_suffix_before_extension(path, v)
            data_to_write = None
            try:
                identifier = int(k)
                try:
                    data_to_write = self.data[identifier]
                    # self.data[i].write(full_path)
                except IndexError:
                    warning(
                        f"No data for item number {identifier}. Cannot write this output"
                    )
            except TypeError:
                identifier = str(k)
                data_to_write = getattr(self, identifier)  # .write(full_path)
            if data_to_write is not None:
                try:
                    data_to_write.write(full_path)
                except NotImplementedError:
                    warning(f"Cannot write output in data item {identifier}. ")
                    continue

    def get_output_path_to_item(self, actor_output_path, item):
        """This method is intended to be called from an ActorOutput object which provides the path.
        It returns the amended path to the specific item, e.g. the numerator or denominator in a QuotientDataItem.
        Do not override this method.
        """
        if self._tuple_length > 1:
            return insert_suffix_before_extension(
                actor_output_path, self._get_output_config()[item]
            )
        else:
            return actor_output_path

    def _get_output_config(self):
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
                return_values = []
                for m in methods_in_data:
                    return_values.append(m(*args, **kwargs))
                return tuple(return_values)

            return hand_down
        else:
            raise AttributeError(f"No such attribute '{item}'")


class SingleArray(DataItemContainer):

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__((ArrayDataItem,), *args, **kwargs)


class DoubleArray(DataItemContainer):

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__((ArrayDataItem, ArrayDataItem), *args, **kwargs)


class SingleItkImage(DataItemContainer):

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__((ItkImageDataItem,), *args, **kwargs)


class QuotientItkImage(DataItemContainer):

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__((ItkImageDataItem, ItkImageDataItem), *args, **kwargs)
        # extend configuration from super class which suffix should be used for which output
        # here: 'numerator' for self.data[0], 'denominator' for self.data[1],
        # and 'quotient' for the property 'quotient', i.e. this data item writes the quotient as additional output
        self.custom_output_config.update(
            {0: "numerator", 1: "denominator", "quotient": "quotient"}
        )

    @property
    def quotient(self):
        return self.numerator / self.denominator


available_data_container_classes = {
    "SingleItkImage": SingleItkImage,
    "QuotientItkImage": QuotientItkImage,
    "SingleArray": SingleArray,
    "DoubleArray": DoubleArray,
}
