from pathlib import Path
from copy import deepcopy
from box import Box

from ..base import GateObject
from ..utility import insert_suffix_before_extension, ensure_filename_is_str
from ..exception import warning, fatal, GateImplementationError
from .dataitems import (
    SingleItkImage,
    SingleMeanItkImage,
    SingleItkImageWithVariance,
    QuotientItkImage,
    QuotientMeanItkImage,
)


def _setter_hook_belongs_to(self, belongs_to):
    if belongs_to is None:
        fatal("The belongs_to attribute of an ActorOutput cannot be None.")
    try:
        belongs_to_name = belongs_to.name
    except AttributeError:
        belongs_to_name = belongs_to
    return belongs_to_name


def _setter_hook_active(self, active):
    if self.__can_be_deactivated__ is True:
        return bool(active)
    else:
        if bool(active) is not True:
            warning(
                f"The output {self.name} of actor {self.belongs_to_actor.name} cannot be deactivated."
            )
        return True


class ActorOutputBase(GateObject):
    user_info_defaults = {
        "belongs_to": (
            None,
            {
                "doc": "Name of the actor to which this output belongs.",
                "setter_hook": _setter_hook_belongs_to,
                "required": True,
            },
        ),
        # "output_filename": (
        #     "auto",
        #     {
        #         "doc": "Filename for the data represented by this actor output. "
        #         "Relative paths and filenames are taken "
        #         "relative to the global simulation output folder "
        #         "set via the Simulation.output_dir option. ",
        #     },
        # ),
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
        "active": (
            True,
            {
                "doc": "Should this output be calculated by the actor? "
                "Note: Output can be deactivated on in certain actors. ",
                "setter_hook": _setter_hook_active,
            },
        ),
    }

    def __init__(self, *args, active=True, **kwargs):
        super().__init__(*args, **kwargs)

        self.data_per_run = {}  # holds the data per run in memory
        self.merged_data = None  # holds the data merged from multiple runs in memory
        # internal flag which can set by the actor when it creating an actor output
        # via _add_actor_output
        # __can_be_deactivated = False forces the "active" user info to True
        # This is the expected behavior in most digitizers
        # In the DoseActor, on the other hand, users might not want to calculate uncertainty
        self.__can_be_deactivated__ = False
        # self._active = active

    def __len__(self):
        return len(self.data_per_run)

    def __getitem__(self, which):
        return self.get_data(which, None)

    # @property
    # def active(self):
    #     return self._active

    # @property
    # def write_to_disk(self):
    #     d = Box([(k, v["write_to_disk"]) for k, v in self.data_item_config.items()])
    #     if len(d) > 1:
    #         return d
    #     elif len(d) == 1:
    #         return list(d.values())[0]
    #     else:
    #         fatal("Nothing defined in data_item_config. ")
    #
    # @write_to_disk.setter
    # def write_to_disk(self, value):
    #     self.set_write_to_disk("all", value)

    def set_write_to_disk(self, value, **kwargs):
        raise NotImplementedError

    def get_write_to_disk(self, **kwargs):
        raise NotImplementedError

    def need_to_write_data(self, **kwargs):
        raise NotImplementedError

    def set_output_filename(self, value, **kwargs):
        raise NotImplementedError

    def get_output_filename(self, **kwargs):
        raise NotImplementedError

    def get_active(self, **kwargs):
        raise NotImplementedError

    def set_active(self, value, **kwargs):
        raise NotImplementedError

    @property
    def belongs_to_actor(self):
        return self.simulation.actor_manager.get_actor(self.belongs_to)

    def initialize(self):
        pass
        # self.initialize_output_filename()

    # def initialize_output_filename(self):
    #     for k, v in self.data_item_config.items():
    #         if 'write_to_disk' in v and v['write_to_disk'] is True:
    #             if 'output_filename' not in v or v['output_filename'] in ['auto', '', None]:
    #                 if len(self.data_item_config) > 0:
    #                     item_suffix = k
    #                 else:
    #                     item_suffix = ''
    #                 v['output_filename'] = f"{self.name}_from_{self.belongs_to_actor.type_name.lower()}_{self.belongs_to_actor.name}_{item_suffix}.{self.default_suffix}"

    def write_data_if_requested(self, *args, **kwargs):
        if self.need_to_write_data():
            self.write_data(*args, **kwargs)

    def _compose_output_path(self, which, output_filename):
        full_data_path = self.simulation.get_output_path(output_filename)

        if which == "merged":
            return full_data_path
        else:
            try:
                run_index = int(which)
            except ValueError:
                fatal(
                    f"Invalid argument 'which' in get_output_path() method "
                    f"of {type(self).__name__} called {self.name}"
                    f"Valid arguments are a run index (int) or the term 'merged'. "
                )
            return insert_suffix_before_extension(full_data_path, f"run{run_index:04f}")

    def get_output_path(
        self, **kwargs
    ):
        raise NotImplementedError

    def get_output_path_as_string(self, **kwargs):
        return ensure_filename_is_str(self.get_output_path(**kwargs))

    def close(self):
        if self.keep_data_in_memory is False:
            self.data_per_run = {}
            self.merged_data = None
        super().close()

    def get_data(self, *args, **kwargs):
        raise NotImplementedError("This is the base class. ")

    def store_data(self, *args, **kwargs):
        raise NotImplementedError("This is the base class. ")

    def write_data(self, *args, **kwargs):
        raise NotImplementedError("This is the base class. ")

    def load_data(self, which):
        raise NotImplementedError(
            f"Your are calling this method from the base class {type(self).__name__}, "
            f"but it should be implemented in the specific derived class"
        )


class InterfaceToActorOutput:

    def __init__(self, belongs_to_actor, user_output_name, item):
        print(f"In ActorOutputShortCut: {repr(user_output_name)}")
        self.user_output_name = user_output_name
        self.belongs_to_actor = belongs_to_actor
        self.item = item
        self._active = True

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["belongs_to_actor"] = None
        return return_dict

    @property
    def _user_output(self):
        return self.belongs_to_actor.user_output[self.user_output_name]

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, value):
        self._active = bool(value)

    def get_output_path(self, **kwargs):
        kwargs.pop("item", None)
        return self._user_output.get_output_path(item=self.item, **kwargs)

    @property
    def write_to_disk(self, **kwargs):
        kwargs.pop("item", None)
        return self._user_output.get_write_to_disk(item=self.item, **kwargs)

    @write_to_disk.setter
    def write_to_disk(self, value, **kwargs):
        self._user_output.set_write_to_disk(value, self.item)

    @property
    def output_filename(self, **kwargs):
        kwargs.pop("item", None)
        return self._user_output.get_output_filename(item=self.item, **kwargs)

    @output_filename.setter
    def output_filename(self, value, **kwargs):
        self._user_output.set_output_filename(value, self.item)


class InterfaceToActorOutputImage(InterfaceToActorOutput):

    @property
    def image(self):
        return self._user_output.get_data(item=self.item)


class ActorOutputUsingDataItemContainer(ActorOutputBase):
    user_info_defaults = {
        "data_item_config": (
            Box({0: Box({"output_filename": "auto", "write_to_disk": True, "active": True})}),
            {
                "doc": "Dictionary (Box) to specify which"
                       "should be written to disk and how. "
                       "The default is picked up from the data container class during instantiation, "
                       "and can be changed by the user afterwards. "
            },
        ),
        "merge_method": (
            "sum",
            {
                "doc": "How should images from runs be merged?",
                "allowed_values": ("sum",),
            },
        ),
        "auto_merge": (
            True,
            {
                "doc": "In case the simulation has multiple runs, should results from separate runs be merged?"
            },
        ),
    }

    data_container_class = None

    def __init__(self, *args, **kwargs):
        if self.data_container_class is None:
            raise GateImplementationError(
                f"No 'data_container_class' class attribute "
                f"specified for class {type(self)}."
            )
        # if type(data_container_class) is type:
        #     if DataItemContainer not in data_container_class.mro():
        #         fatal(f"Illegal data container class {data_container_class}. ")
        #     self.data_container_class = data_container_class
        # else:
        #     try:
        #         self.data_container_class = available_data_container_classes[
        #             data_container_class
        #         ]
        #     except KeyError:
        #         fatal(
        #             f"Unknown data item class {data_container_class}. "
        #             f"Available classes are: {list(available_data_container_classes.keys())}"
        #         )
        data_item_config = kwargs.pop("data_item_config", None)
        super().__init__(*args, **kwargs)
        if data_item_config is None:
            # get the default write config from the container class
            self.data_item_config = (
                self.data_container_class.get_default_data_item_config()
            )
        else:
            # set the parameters provided by the user in kwargs
            self.data_item_config = data_item_config
        # temporary fix to guarantee there is an 'output_filename' in data_item_config
        for k, v in self.data_item_config.items():
            if "output_filename" not in v:
                v["output_filename"] = str(
                    insert_suffix_before_extension(self.output_filename, v["suffix"])
                )

    # def get_output_path(self, **kwargs):
    #     item = kwargs.pop("item", "all")
    #     if item is None:
    #         return super().get_output_path(**kwargs)
    #     else:
    #         return super().get_output_path(
    #             output_filename=self.get_output_filename(item=item), **kwargs
    #         )
    #
    # def get_output_filename(self, *args, item="all"):
    #     if item == "all":
    #         return Box(
    #             [
    #                 (k, str(self.compose_output_path_to_item(self.output_filename, k)))
    #                 for k in self.data_item_config
    #             ]
    #         )
    #     else:
    #         return str(self.compose_output_path_to_item(self.output_filename, item))

    # def compose_output_path_to_item(self, output_path, item):
    #     """This method is intended to be called from an ActorOutput object which provides the path.
    #     It returns the amended path to the specific item, e.g. the numerator or denominator in a QuotientDataItem.
    #     Do not override this method.
    #     """
    #     return insert_suffix_before_extension(
    #         output_path, self._get_suffix_for_item(item)
    #     )
    #     # else:
    #     #     return actor_output_path

    # def _get_suffix_for_item(self, identifier):
    #     if identifier in self.data_item_config:
    #         return self.data_item_config[identifier]["suffix"]
    #     else:
    #         fatal(
    #             f"No data item found with identifier {identifier} "
    #             f"in container class {self.data_container_class.__name__}. "
    #             f"Valid identifiers are: {list(self.data_item_config.keys())}."
    #         )

    # override methods:
    def set_write_to_disk(self, value, item=0):
        if item == "all":
            for k in self.data_item_config.keys():
                self.set_write_to_disk(value, k)
        else:
            try:
                self.data_item_config[item]["write_to_disk"] = bool(value)
            except KeyError:
                fatal(
                    f"Unknown item {item}. Known items are {list(self.data_item_config.keys())}."
                )

    def get_write_to_disk(self, item=0):
        if item == "all":
            return Box(
                [(k, v["write_to_disk"]) for k, v in self.data_item_config.items()]
            )
        else:
            try:
                return self.data_item_config[item]["write_to_disk"]
            except KeyError:
                fatal(
                    f"Unknown item {item}. Known items are {list(self.data_item_config.keys())}."
                )

    def need_to_write_data(self, **kwargs):
        return any([v["write_to_disk"] is True for v in self.data_write_config.values()])

    def set_output_filename(self, value, item=0):
        if item == "all":
            for k in self.data_item_config.keys():
                self.set_output_filename(insert_suffix_before_extension(value, k), k)
        else:
            try:
                self.data_item_config[item]["output_filename"] = str(value)
            except KeyError:
                fatal(
                    f"Unknown item {item}. Known items are {list(self.data_item_config.keys())}."
                )

    def get_output_filename(self, item=0):
        if item == "all":
            fatal(
                f"get_output_filename() does not accept item='all', only existing items. "
                f"This actor output has the following items: {list(self.data_item_config.keys())}. "
            )
        else:
            try:
                f = self.data_item_config[item]["output_filename"]
            except KeyError:
                fatal(
                    f"Unknown item {item}. Known items are {list(self.data_item_config.keys())}."
                )
            if f == "auto":
                if len(self.data_item_config) > 0:
                    item_suffix = item
                else:
                    item_suffix = ""
                output_filename = f"{self.name}_from_{self.belongs_to_actor.type_name.lower()}_{self.belongs_to_actor.name}_{item_suffix}.{self.default_suffix}"
            else:
                output_filename = f
        return output_filename

    def get_output_path(
        self, which="merged", item=0, always_return_dict=False, **kwargs
    ):

        if item == "all":
            items = [
                k
                for k, v in self.data_item_config.items()
                if v["write_to_disk"] is True
            ]
        elif isinstance(item, (tuple, list)):
            items = item
        else:
            items = [item]

        return_dict = {}
        for i in items:
            output_filename = self.get_output_filename(item=i)
            return_dict[i] = self._compose_output_path(which, output_filename)
        if len(return_dict) > 1 or always_return_dict is True:
            return return_dict
        else:
            return list(return_dict.values())[0]

    def merge_data(self, list_of_data):
        if self.merge_method == "sum":
            merged_data = list_of_data[0]
            for d in list_of_data[1:]:
                merged_data.inplace_merge_with(d)
            return merged_data

    def merge_data_from_runs(self):
        self.merged_data = self.merge_data(list(self.data_per_run.values()))

    def merge_into_merged_data(self, data):
        if self.merged_data is None:
            self.merged_data = data
        else:
            self.merged_data = self.merge_data([self.merged_data, data])

    def end_of_run(self, run_index):
        if self.auto_merge is True:
            self.merge_into_merged_data(self.data_per_run[run_index])
        if self.keep_data_per_run is False:
            self.data_per_run.pop(run_index)

    def end_of_simulation(self):
        self.write_data_if_requested("all")
        # if self.auto_merge is True:
        #     self.merge_data_from_runs()
        # if self.keep_data_per_run is False:
        #     for k in self.data_per_run:
        #         self.data_per_run[k] = None

    def get_data_container(self, which):
        if which == "merged":
            return self.merged_data
        else:
            try:
                run_index = int(which)  # might be a run_index
                if (
                    run_index in self.data_per_run
                    and self.data_per_run[run_index] is not None
                ):
                    return self.data_per_run[run_index]
                else:
                    fatal(f"No data stored for run index {run_index}")
            except ValueError:
                fatal(
                    f"Invalid argument 'which' in get_data_container() method of ActorOutput {self.name}. "
                    f"Allowed values are: 'merged' or a valid run_index. "
                )

    def get_data(self, which="merged", item=None):
        container = self.get_data_container(which)
        if container is None:
            return None
        else:
            return container.get_data(item)

    def store_data(self, which, *data):
        """data can be either the user data to be wrapped into a DataContainer class or
        an already wrapped DataContainer class.
        """

        if isinstance(data, self.data_container_class):
            data_item = data
            data_item.belongs_to = self
        else:
            data_item = self.data_container_class(belongs_to=self, data=data)
        # FIXME: use store_data if target data exists, otherwise create new container
        if which == "merged":
            self.merged_data = data_item
        else:
            try:
                run_index = int(which)  # might be a run_index
                # if run_index not in self.data_per_run:
                # else:
                #     fatal(
                #         f"A data item is already set for run index {run_index}. "
                #         f"You can only merge additional data into it. Overwriting is not allowed. "
                #     )
            except ValueError:
                fatal(
                    f"Invalid argument 'which' in store_data() method of ActorOutput {self.name}. "
                    f"Allowed values are: 'merged' or a valid run_index. "
                )
            self.data_per_run[run_index] = data_item

    def store_meta_data(self, which, **meta_data):
        """data can be either the user data to be wrapped into a DataContainer class or
        an already wrapped DataContainer class.
        """

        if which == "merged":
            data = self.merged_data
        else:
            try:
                run_index = int(which)  # might be a run_index
            except ValueError:
                fatal(
                    f"Invalid argument 'which' in store_data() method of ActorOutput {self.name}. "
                    f"Allowed values are: 'merged' or a valid run_index. "
                )
            data = self.data_per_run[run_index]
        if data is None:
            fatal(
                f"Cannot store meta data because no data exists yet for which='{which}'."
            )
        data.update_meta_data(meta_data)

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

    def write_data(self, which, **kwargs):
        if which == "all_runs":
            for k in self.data_per_run.keys():
                self.write_data(k, **kwargs)
        elif which == "all":
            self.write_data("all_runs", **kwargs)
            self.write_data("merged", **kwargs)
        else:
            data = self.get_data_container(which)
            if data is not None:
                data.write(
                    self.get_output_path(which=which, always_return_dict=True, **kwargs)
                )


class ActorOutputImage(ActorOutputUsingDataItemContainer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_suffix = "mhd"

    def set_image_properties(self, which, **kwargs):
        for image_data in self.collect_data(which):
            if image_data is not None:
                image_data.set_image_properties(**kwargs)

    def get_image_properties(self, which, item=0):
        if which == "merged":
            if self.merged_data is not None:
                return self.merged_data.get_image_properties()[item]
        else:
            try:
                run_index = int(which)
                try:
                    image_data_container = self.data_per_run[run_index]
                except KeyError:
                    fatal(f"No data found for run index {run_index}.")
                if image_data_container is not None:
                    return image_data_container.get_image_properties()[item]
            except ValueError:
                fatal(
                    f"Illegal argument 'which'. Provide a valid run index or the term 'merged'."
                )

    def create_empty_image(self, run_index, size, spacing, origin=None, **kwargs):
        if run_index not in self.data_per_run:
            self.data_per_run[run_index] = self.data_container_class(belongs_to=self)
        self.data_per_run[run_index].create_empty_image(
            size, spacing, origin=origin, **kwargs
        )


# concrete classes usable in Actors:
class ActorOutputSingleImage(ActorOutputImage):
    data_container_class = SingleItkImage

    # def __init__(self, *args, **kwargs):
    #     super().__init__("SingleItkImage", *args, **kwargs)
    #


class ActorOutputSingleMeanImage(ActorOutputImage):
    data_container_class = SingleMeanItkImage
    # def __init__(self, *args, **kwargs):
    #     super().__init__("SingleMeanItkImage", *args, **kwargs)


class ActorOutputSingleImageWithVariance(ActorOutputImage):
    data_container_class = SingleItkImageWithVariance

    # def __init__(self, *args, **kwargs):
    #     super().__init__("SingleItkImageWithVariance", *args, **kwargs)


class ActorOutputQuotientImage(ActorOutputImage):
    data_container_class = QuotientItkImage
    # def __init__(self, *args, **kwargs):
    #     super().__init__("QuotientItkImage", *args, **kwargs)


class ActorOutputQuotientMeanImage(ActorOutputImage):
    data_container_class = QuotientMeanItkImage

    # def __init__(self, *args, **kwargs):
    #     super().__init__("QuotientMeanItkImage", *args, **kwargs)


class ActorOutputRoot(ActorOutputBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_suffix = "root"

    def get_output_path(self, *args, **kwargs):
        return super().get_output_path("merged")

    def initialize(self):
        # for ROOT output, do not set a default output_filename
        # we just DON'T want to dump the file
        if self.output_filename == "" or self.output_filename is None:
            self.write_to_disk = False
        super().initialize()


class ActorOutputCppImage(ActorOutputBase):
    """Simple actor output class to provide the get_output_path() interface
    to actors where the image is entirely handled on the C++-side.

    This actor output does not provide any further functionality and cannot merge data from runs.

    If possible, the actor should be implemented in a way to make use of the ActorOutputImage class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_suffix = "root"

    def get_output_path(self, *args, **kwargs):
        return super().get_output_path("merged")
