import numpy as np
import json
from box import Box

from ..exception import fatal, warning, GateImplementationError
from ..utility import insert_suffix_before_extension, ensure_filename_is_str, g4_units
from ..image import (
    sum_itk_images,
    divide_itk_images,
    multiply_itk_images,
    scale_itk_image,
    create_3d_image,
    write_itk_image,
    get_info_from_image,
)


# base classes
class DataItem:

    def __init__(self, *args, data=None, meta_data=None, **kwargs):
        self.data = None
        if data is not None:
            self.set_data(data)
        self.meta_data = Box()
        if meta_data:
            try:
                for k, v in meta_data.items():
                    self.meta_data[k] = v
            except AttributeError:
                fatal(f"Illegal keyword argument meta_data: {meta_data}. "
                      f"Should be a dictionary-like object, but found {type(meta_data)}.")

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
        # check if any of the data items has this attribute
        # exclude 'data' to avoid infinite recursion
        # exclude '__setstate__' and '__getstate__' to avoid interference with pickling
        if item not in ("data", "__setstate__", "__getstate__"):
            if hasattr(self.data, item):
                if callable(getattr(self.data, item)):

                    def hand_down(*args, **kwargs):
                        getattr(self.data, item)(*args, **kwargs)

                    return hand_down
            else:
                raise AttributeError(f"No such attribute '{item}'")
        else:
            raise AttributeError(f"No such attribute '{item}'")

    def merge_with(self, other):
        """The base class implements merging as summation.
        Specific classes can override this, e.g. to merge mean values.
        """
        return self + other

    def inplace_merge_with(self, other):
        """The base class implements merging as summation.
        Specific classes can override this, e.g. to merge mean values.
        """
        self += other
        return self

    def write(self, *args, **kwargs):
        raise NotImplementedError(f"This is the base class. ")


class MeanValueDataItemMixin:
    """This class cannot be instantiated on its own.
    It is solely meant to be mixed into a class that inherits from DataItem (or daughters).
    Important: It must appear before the main base class in the inheritance order so that the
    overloaded methods take priority.
    """

    @property
    def number_of_samples(self):
        try:
            return self.meta_data['number_of_samples']
        except KeyError:
            fatal(f"This data item holds a mean value, "
                  f"but the meta_data dictionary does not contain any value for 'number_of_samples'.")

    @number_of_samples.setter
    def number_of_samples(self, value):
        self.meta_data['number_of_samples'] = int(value)

    def merge_with(self, other):
        result = ((self * self.number_of_samples + other * other.number_of_samples) /
                    (self.number_of_samples + other.number_of_samples))
        result.number_of_samples = self.number_of_samples + other.number_of_samples
        return result

    def inplace_merge_with(self, other):
        self *= self.number_of_samples
        other *= other.number_of_samples
        self += other
        self /= (self.number_of_samples + other.number_of_samples)
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
        self._assert_data_is_not_none()
        self.set_data(sum_itk_images([self.data, other.data]))
        return self

    def __add__(self, other):
        self._assert_data_is_not_none()
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
            return type(self)(data=scale_itk_image(self.data, 1. / other))
        else:
            return type(self)(data=divide_itk_images(self.data, other.data))

    def __itruediv__(self, other):
        self._assert_data_is_not_none()
        if isinstance(other, (float, int)):
            self.set_data(scale_itk_image(self.data, 1. / other))
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
                self.data.SetDirection(properties["rotation"])

    def get_image_properties(self):
        return get_info_from_image(self.data)

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

    def __init__(self, *args, data=None, **kwargs):
        super().__init__(*args, **kwargs)

        # create the instances of the data item classes
        # and populate them with data if provided
        self.data = [dic(data=None) for dic in self._data_item_classes]
        if data is not None:
            self.set_data(*data)

    @classmethod
    def get_default_data_write_config(cls):
        default_data_write_config = None
        # try to pick up data write config defined in the specific class or base classes
        for c in cls.mro():
            try:
                default_data_write_config = c.__dict__["default_data_write_config"]
                break
            except KeyError:
                continue
        # If none of the classes in the inheritance chain specifies data item,
        # we fill up a dictionary with the default configuration
        if default_data_write_config is None:
            if len(cls._data_item_classes) > 1:
                default_data_write_config = Box(
                    [
                        (i, Box({"suffix": f"dataitem_{i}", "write_to_disk": True}))
                        for i in range(len(cls._data_item_classes))
                    ]
                )
            else:
                # no special suffix for single-item containers
                default_data_write_config = Box(
                    {0: Box({"suffix": None, "write_to_disk": True})}
                )
        return default_data_write_config

    # the actual write config needs to be fetched from the actor output instance
    # which handles this data item container
    @property
    def data_write_config(self):
        try:
            return self.belongs_to.data_write_config
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
            d.meta_data.update(meta_data)

    def set_data(self, *data):
        # data might be already contained in the correct container class,
        # or intended to be the input to the container class
        processed_data = []
        for d, c in zip(data, self._data_item_classes):
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
        return self.propagate_operator_inplace(other, '__iadd__')

    def __add__(self, other):
        return self.propagate_operator(other, '__add__')

    def __imul__(self, other):
        return self.propagate_operator_inplace(other, '__imul__')

    def __mul__(self, other):
        return self.propagate_operator(other, '__mul__')

    def __itruediv__(self, other):
        return self.propagate_operator_inplace(other, '__itruediv__')

    def __truediv__(self, other):
        return self.propagate_operator(other, '__truediv__')

    def inplace_merge_with(self, other):
        self._assert_data_is_not_none()
        for i in range(self._tuple_length):
            self.data[i].inplace_merge_with(other.data[i])
        return self

    def merge_with(self, other):
        self._assert_data_is_not_none()
        return type(self)(
            self._data_item_classes,
            data=[
                self.data[i].merge_with(other.data[i])
                for i in range(self._tuple_length)
            ],
        )

    def write(self, path, item=None):
        if item is None:
            items_to_write = [
                k
                for k, v in self.data_write_config.items()
                if v["write_to_disk"] is True
            ]
        else:
            items_to_write = [item]
        for k in items_to_write:
            full_path = self.belongs_to.compose_output_path_to_item(path, k)
            try:
                identifier = int(k)
                try:
                    data_to_write = self.data[identifier]
                    # self.data[i].write(full_path)
                except IndexError:
                    data_to_write = None
                    warning(
                        f"No data for item number {identifier}. Cannot write this output"
                    )
            except ValueError:
                identifier = str(k)
                data_to_write = getattr(self, identifier)  # .write(full_path)
            if data_to_write is not None:
                try:
                    data_to_write.write(full_path)
                except NotImplementedError:
                    warning(f"Cannot write output in data item {identifier}. ")
                    continue

    def __getattr__(self, item):
        # check if any of the data items has this attribute
        # exclude 'data' to avoid infinite recursion
        # exclude '__setstate__' and '__getstate__' to avoid interference with pickling
        if item not in ("data", "__setstate__", "__getstate__"):
            methods_in_data = []
            attributes_in_data = []
            for d in self.data:
                if hasattr(d, item):
                    if callable(getattr(d, item)):
                        methods_in_data.append(getattr(d, item))
                    else:
                        attributes_in_data.append(getattr(d, item))
            if len(attributes_in_data) > 0 and len(methods_in_data) > 0:
                fatal(f"Cannot hand down request for attribute to data items "
                      f"because some contain it as a method and other as a property. ")
            elif len(attributes_in_data) > 0:
                if len(attributes_in_data) != len(self.data):
                    fatal(f"Cannot hand down request for property to data items "
                          f"because not all of them contain it. ")
                if len(attributes_in_data) == 1:
                    return attributes_in_data[0]
                else:
                    return attributes_in_data
            elif len(methods_in_data) > 0:
                if len(methods_in_data) != len(self.data):
                    fatal(f"Cannot hand down request for method to data items "
                          f"because not all of them contain it. ")
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

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__(*args, **kwargs)


class DoubleArray(DataItemContainer):

    _data_item_classes = (ArrayDataItem, ArrayDataItem)

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__(*args, **kwargs)


class SingleItkImage(DataItemContainer):

    _data_item_classes = (ItkImageDataItem,)

    @property
    def image(self):
        return self.data[0].image


class SingleMeanItkImage(DataItemContainer):

    _data_item_classes = (MeanItkImageDataItem,)


class QuotientItkImage(DataItemContainer):

    _data_item_classes = (
        ItkImageDataItem,
        ItkImageDataItem,
    )

    # Specify which items should be written to disk and how
    # Important: define this at the class level, NOT in the __init__ method
    default_data_write_config = Box(
        {
            "numerator": Box({"suffix": "numerator", "write_to_disk": True}),
            "denominator": Box({"suffix": "denominator", "write_to_disk": True}),
            "quotient": Box({"suffix": "quotient", "write_to_disk": True}),
        }
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

    @property
    def images(self):
        return self.data[0].image, self.data[0].image

    @property
    def numerator_image(self):
        return self.numerator.image

    @property
    def denominator_image(self):
        return self.denominator.image


available_data_container_classes = {
    "SingleItkImage": SingleItkImage,
    "QuotientItkImage": QuotientItkImage,
    "SingleArray": SingleArray,
    "DoubleArray": DoubleArray,
}
