import itk
import numpy as np
import json
from box import Box

from ..exception import fatal, warning, GateImplementationError
from ..utility import ensure_filename_is_str, calculate_variance
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
        try:
            return self + other
        except ValueError as e:
            raise NotImplementedError(
                f"method 'merge_with' probably not implemented for data item class {type(self)} "
                f"because the following ValueError was encountered: \n{e}"
            )

    def inplace_merge_with(self, other):
        """The base class implements merging as summation.
        Specific classes can override this, e.g. to merge mean values.
        """
        try:
            self += other
        except ValueError as e:
            raise NotImplementedError(
                f"method 'inplace_merge_with' probably not implemented for data item class {type(self)} "
                f"because the following ValueError was encountered: \n{e}"
            )
        return self

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
                self.data.SetDirection(properties["rotation"])

    def get_image_properties(self):
        return get_info_from_image(self.data)

    def copy_image_properties(self, other_image):
        self.data.CopyInformation(other_image)

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
    def get_default_data_item_config(cls):
        default_data_item_config = None
        # try to pick up data write config defined in the specific class or base classes
        for c in cls.mro():
            try:
                default_data_item_config = c.__dict__["default_data_item_config"]
                break
            except KeyError:
                continue
        # If none of the classes in the inheritance chain specifies data item,
        # we fill up a dictionary with the default configuration
        if default_data_item_config is None:
            default_data_item_config = Box(
                [
                    (
                        i,
                        Box(
                            {
                                "output_filename": "auto",
                                "write_to_disk": True,
                                "active": True,
                            }
                        ),
                    )
                    for i in range(len(cls._data_item_classes))
                ]
            )
            if len(default_data_item_config) == 1:
                list(default_data_item_config.values())[0]["suffix"] = None
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
        try:
            identifier = int(item)
            try:
                return self.data[identifier]
            except IndexError:
                return None
        except ValueError:
            return getattr(self, str(item), None)

    def get_data(self, item=0):
        try:
            item_index = int(item)
            try:
                return self.data[item_index].data
            except IndexError:
                pass
                # fatal(f"No data found for index {item_index}. ")
        except ValueError:
            try:
                return getattr(self, item).data
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
            if (
                (self.data[i] is not None)
                and (other.data[i] is not None)
                and (self.data[i].data is not None)
                and (other.data[i].data is not None)
            ):
                self.data[i].inplace_merge_with(other.data[i])
            else:
                # the case of both item None is acceptable
                # because the component not be activated in the actor, e.g. edep uncertainty,
                # but it should not occur that one item is None and the other is not.
                if (self.data[i] is None or self.data[i].data is None) is not (
                    other.data[i] is None or other.data[i].data is None
                ):
                    s_not = {True: "", False: "not_"}
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
            data_item.write(path)
        else:
            warning(f"Cannot write item {item} because it does not exist (=None).")

    def __getattr__(self, item):
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


class SingleItkImageWithVariance(DataItemContainer):

    _data_item_classes = (
        ItkImageDataItem,
        ItkImageDataItem,
    )

    # Only the linear quantity is active by default
    # the uncertainty quantity has write_to_disk=True by default so whenever it is activated,
    # the results will be written to disk (probably the expected default behavior in most cases)
    default_data_item_config = Box(
        {
            0: Box({"output_filename": "auto", "write_to_disk": True, "active": True}),
            1: Box(
                {"output_filename": "auto", "write_to_disk": False, "active": False}
            ),
            "variance": Box(
                {"output_filename": "auto", "write_to_disk": False, "active": False}
            ),
            "std": Box(
                {"output_filename": "auto", "write_to_disk": False, "active": False}
            ),
            "uncertainty": Box(
                {"output_filename": "auto", "write_to_disk": True, "active": False}
            ),
        }
    )

    def get_variance_or_uncertainty(self, which_quantity):
        try:
            # if not self.data[0].number_of_samples == self.data[1].number_of_samples:
            #     fatal(f"Something is wrong in this data item container: "
            #           f"the two data items contain different numbers of samples. ")
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
                    "The variance will be set to 1 everywhere. "
                )
                output_arr = np.ones_like(value_array)
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
                        out=np.ones_like(output_arr),
                        where=value_array != 0,
                    )
            output_image = itk.image_view_from_array(output_arr)
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


class QuotientItkImage(DataItemContainer):

    _data_item_classes = (
        ItkImageDataItem,
        ItkImageDataItem,
    )

    # Specify which items should be written to disk and how
    # Important: define this at the class level, NOT in the __init__ method
    default_data_item_config = Box(
        {
            0: Box({"output_filename": "auto", "write_to_disk": True, "active": True}),
            1: Box({"output_filename": "auto", "write_to_disk": True, "active": True}),
            "quotient": Box(
                {"output_filename": "auto", "write_to_disk": True, "active": True}
            ),
        }
    )

    @property
    def quotient(self):
        return self.data[0] / self.data[1]


class QuotientMeanItkImage(QuotientItkImage):

    _data_item_classes = (
        MeanItkImageDataItem,
        MeanItkImageDataItem,
    )


def merge_data(list_of_data):
    merged_data = list_of_data[0]
    for d in list_of_data[1:]:
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
