import itk
import numpy as np
import json
from box import Box

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
        self.data = None
        if data is not None:
            self.set_data(data)

    def set_data(self, data, **kwargs):
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
        # try to pick up writable dataitems defined in the specific class
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
            belongs_to = self.belongs_to
        except AttributeError:
            raise AttributeError("belongs_to unknown")
        return self.belongs_to.data_write_config

    @property
    def _tuple_length(self):
        return len(self._data_item_classes)

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

    def __iadd__(self, other):
        self._assert_data_is_not_none()
        for i in range(self._tuple_length):
            self.data[i].__iadd__(other.data[i])
        return self

    def __add__(self, other):
        self._assert_data_is_not_none()
        return type(self)(
            self._data_item_classes,
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
            self._data_item_classes,
            data=[
                self.data[i].__truediv__(other.data[i])
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
            full_path = self.get_output_path_to_item(path, k)
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

    def get_output_path_to_item(self, actor_output_path, item=None):
        """This method is intended to be called from an ActorOutput object which provides the path.
        It returns the amended path to the specific item, e.g. the numerator or denominator in a QuotientDataItem.
        Do not override this method.
        """
        if self._tuple_length > 1 and item is None:
            fatal(
                f"This data container holds {self._tuple_length} data items. "
                f"You must provide an item=... argument. "
                f"Valid writable items of this container are: {list(self.data_write_config.keys())}."
            )
        return insert_suffix_before_extension(
            actor_output_path, self._get_suffix_for_item(item)
        )
        # else:
        #     return actor_output_path

    def _get_suffix_for_item(self, identifier):
        if identifier in self.data_write_config:
            return self.data_write_config[identifier]["suffix"]
        else:
            fatal(
                f"No data item found with identifier {identifier} "
                f"in container class {type(self).__name__}."
            )
            # try:
            #     suffix = f"dataitem_{int(identifier)}"
            # except ValueError:
            #     suffix = str(identifier)
        # return suffix

    def __getattr__(self, item):
        # check if any of the data items has this attribute
        # exclude 'data' to avoid infinite recursion
        # exclude '__setstate__' and '__getstate__' to avoid interference with pickling
        if item not in ("data", "__setstate__", "__getstate__"):
            methods_in_data = []
            for d in self.data:
                if hasattr(d, item):
                    if callable(getattr(d, item)):
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

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__(*args, **kwargs)

    @property
    def image(self):
        return self.data[0].image


class QuotientItkImage(DataItemContainer):

    _data_item_classes = ((ItkImageDataItem, ItkImageDataItem),)

    # Specify which items should be written to disk and how
    # Important: define this at the class level, NOT in the __init__ method
    default_data_write_config = Box(
        {
            "numerator": Box({"suffix": "numerator", "write_to_disk": True}),
            "denominator": Box({"suffix": "denominator", "write_to_disk": True}),
            "quotient": Box({"suffix": "quotient", "write_to_disk": True}),
        }
    )

    def __init__(self, *args, **kwargs):
        # specify the data item classes
        super().__init__(*args, **kwargs)

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
