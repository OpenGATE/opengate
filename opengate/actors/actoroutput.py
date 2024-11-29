import copy
import inspect
from box import Box
from typing import Optional
import sys

import opengate_core as g4
from ..base import GateObject, process_cls
from ..utility import insert_suffix_before_extension, ensure_filename_is_str
from ..exception import warning, fatal, GateImplementationError
from .dataitems import (
    SingleItkImage,
    SingleMeanItkImage,
    SingleItkImageWithVariance,
    QuotientItkImage,
    QuotientMeanItkImage,
    merge_data,
)


def get_formatted_docstring_rst(cls, attr_name, begin_of_line="  - "):
    """Format a property's docstring into a reST bullet point."""
    attr = getattr(cls, attr_name, None)
    if not attr:
        raise GateImplementationError(f"Attribute {attr_name} not found in {cls}.")

    docstring = inspect.getdoc(attr)
    prop_or_func = attr_name
    if inspect.isfunction(attr):
        prop_or_func += "()"

    if not docstring:
        return f"{begin_of_line} **{prop_or_func}**: No description available.\n\n"

    description = " ".join(line.strip() for line in docstring.splitlines())

    return f"{begin_of_line} **{prop_or_func}**: {description}\n\n"


class BaseUserInterfaceToActorOutput:
    # these attributes are known to the class
    # and should be treated differently by __getattr__() and __setattr__(),
    # namely they should be retrieved directly from __dict__
    # or written directly into __dict__ to avoid infinite recursion
    # IMPORTANT: a copy of this list needs to be defined also in __getattr__ and __setattr__
    _known_attributes = (
        "__setstate__",
        "__getstate__",
        "user_output_name",
        "interface_name",
        "belongs_to_actor",
        "_kwargs_for_interface_calls",
    )

    @classmethod
    def __get_docstring_attributes__(cls):
        docstring = ""
        docstring += get_formatted_docstring_rst(cls, "active")
        docstring += get_formatted_docstring_rst(cls, "output_filename")
        docstring += get_formatted_docstring_rst(cls, "write_to_disk")
        docstring += get_formatted_docstring_rst(cls, "keep_data_per_run")
        return docstring

    @classmethod
    def __get_docstring_methods__(cls):
        docstring = ""
        docstring += get_formatted_docstring_rst(cls, "get_output_path")
        docstring += get_formatted_docstring_rst(cls, "get_data")
        return docstring

    def __init__(
        self,
        belongs_to_actor,
        user_output_name,
        interface_name,
        kwargs_for_interface_calls=None,
        **kwargs,
    ):
        # Important: the attributes set here in the __init__ method need to be
        # listed in the _known_attributes class attribute
        # because the __setattr__ method needs that
        self.user_output_name = user_output_name
        self.interface_name = interface_name
        self.belongs_to_actor = belongs_to_actor
        if kwargs_for_interface_calls is None:
            self._kwargs_for_interface_calls = {}
        else:
            self._kwargs_for_interface_calls = kwargs_for_interface_calls

    def __getstate__(self):
        """
        For earlier python version (<3.11), __getstate__ may not be defined.
        We provide a simple workaround here to return a copy of the internal dict.
        """
        return_dict = self.__dict__.copy()
        # set 'belongs_to_actor' to None to avoid pickling circles; will be reset during unpickling
        return_dict["belongs_to_actor"] = None
        return return_dict

    @property
    def _user_output(self):
        return self.belongs_to_actor.user_output[self.user_output_name]

    @property
    def active(self):
        """Should the actor consider and score this output?"""
        try:
            return self._user_output.get_active(**self._kwargs_for_interface_calls)
        except NotImplementedError:
            raise AttributeError

    @active.setter
    def active(self, value):
        self._user_output.set_active(value, **self._kwargs_for_interface_calls)

    def get_output_path(self, which="merged", **kwargs):
        """Get the path (absolute) where GATE stores this output.
        Use the argument 'which' to specify whether you refer to the cumulative output
        of the entire simulation (which='merged'), or to a specific run,
        e.g. which=2 for run index 2 (run indices start at 0).
        """
        kwargs.update(self._kwargs_for_interface_calls)
        return self._user_output.get_output_path(which=which, **kwargs)

    def get_run_indices(self, **kwargs):
        kwargs.update(self._kwargs_for_interface_calls)
        return self._user_output.get_run_indices(**kwargs)

    def get_data(self, which="merged", **kwargs):
        """Get the data stored in this output, e.g. an ITK image.
        Use the argument 'which' to specify whether you refer to the cumulative output
        of the entire simulation (which='merged'), or to a specific run,
        e.g. which=2 for run index 2 (run indices start at 0).
        """
        kwargs.update(self._kwargs_for_interface_calls)
        return self._user_output.get_data(**kwargs)

    @property
    def write_to_disk(self):
        """Should this output be stored on disk?"""
        try:
            return self._user_output.get_write_to_disk(
                **self._kwargs_for_interface_calls
            )
        except NotImplementedError:
            raise AttributeError

    @write_to_disk.setter
    def write_to_disk(self, value):
        self._user_output.set_write_to_disk(value, **self._kwargs_for_interface_calls)

    @property
    def output_filename(self):
        """Output filename used for this output.
        An automatic suffix is appended for per-run data.
        You can also specify a relative path, i.e. relative to the simulation's output directory,
        e.g. output_file = Path('dose_output') / 'patient_dose.mhd'.
        """
        try:
            return self._user_output.get_output_filename(
                **self._kwargs_for_interface_calls
            )
        except NotImplementedError:
            raise AttributeError

    @output_filename.setter
    def output_filename(self, value):
        self._user_output.set_output_filename(value, **self._kwargs_for_interface_calls)

    @property
    def keep_data_per_run(self):
        """Should data be kept in memory for individual runs? If False, only the cumulative data is kept.
        Note: Not every kind of user output supports this, e.g. ROOT output cannot per stored on a per-run basis.
        """
        try:
            return self._user_output.get_keep_data_per_run(
                **self._kwargs_for_interface_calls
            )
        except NotImplementedError:
            raise AttributeError

    @keep_data_per_run.setter
    def keep_data_per_run(self, value):
        self._user_output.keep_data_per_run = value

    @property
    def suffix(self):
        """Specify the automatic suffix to be used for this output in case the output_filename is set
        via the actor for all output handled by the actor.
        The default item suffix is equal to the output name and there should be no need to change it.
        """
        try:
            return self._user_output.get_item_suffix(**self._kwargs_for_interface_calls)
        except NotImplementedError:
            raise AttributeError

    @suffix.setter
    def suffix(self, value):
        self._user_output.set_item_suffix(value, **self._kwargs_for_interface_calls)

    def __getattr__(self, item):
        # Recall: this method is called when python cannot otherwise
        # find the attribute in the instance. In this case, we try to find it
        # in the associated user_output to make the interface transparent

        # try to get known attributes directly from __dict__
        # to avoid infinite recursion
        if item in (
            "__setstate__",
            "__getstate__",
            "user_output_name",
            "interface_name",
            "belongs_to_actor",
            "_kwargs_for_interface_calls",
        ):
            try:
                return self.__dict__[item]
            except KeyError:
                raise AttributeError(f"Could not find known attribute {item}")
        # for the others, use the getattr() builtin
        _user_output = self.belongs_to_actor.user_output[self.user_output_name]
        try:
            return getattr(_user_output, item)
        except AttributeError:
            raise AttributeError(
                f"Tried to find {item} in user output {_user_output.name} "
                "and via the interface to it, but it is not there. "
            )

    def __setattr__(self, item, value):
        # if item in type(self).__dict__["_known_attributes"]:
        if item in (
            "user_output_name",
            "belongs_to_actor",
            "_kwargs_for_interface_calls",
        ):
            self.__dict__[item] = value
        else:
            try:
                super().__setattr__(item, value)
            except NotImplementedError:
                if item in self._user_output.user_info:
                    setattr(self._user_output, item, value)
                else:
                    fatal(
                        f"Unable to set value {value} for item {item}. "
                        "Make sure the actor and/or actor output support this parameter. "
                    )


class UserInterfaceToActorOutputUsingDataItemContainer(BaseUserInterfaceToActorOutput):

    def __init__(self, *args, item=0, **kwargs):
        super().__init__(*args, kwargs_for_interface_calls={"item": item}, **kwargs)


class UserInterfaceToActorOutputImage(UserInterfaceToActorOutputUsingDataItemContainer):

    @classmethod
    def __get_docstring_attributes__(cls):
        docstring = super().__get_docstring_attributes__()
        docstring += get_formatted_docstring_rst(cls, "image")
        return docstring

    @property
    def image(self):
        """Shortcut to the ITK image containing the cumulative result of this actor,
        e.g. the dose scored over the entire simulation. If you need to get the image
        corresponding to a certain run, use get_data(which=RUN_INDEX).
        For example: get_data(which=3) to get the image from run 3 (run indices start at 0).
        """
        return self._user_output.get_data(**self._kwargs_for_interface_calls)


def _setter_hook_belongs_to(self, belongs_to):
    if belongs_to is None:
        fatal("The belongs_to attribute of an ActorOutput cannot be None.")
    try:
        belongs_to_name = belongs_to.name
    except AttributeError:
        belongs_to_name = belongs_to
    return belongs_to_name


class ActorOutputBase(GateObject):
    # hints for IDE
    belongs_to: str
    keep_data_in_memory: bool

    _default_interface_class = BaseUserInterfaceToActorOutput
    default_suffix = None

    user_info_defaults = {
        "belongs_to": (
            None,
            {
                "doc": "Name of the actor to which this output belongs.",
                "setter_hook": _setter_hook_belongs_to,
                "required": True,
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
    }

    @classmethod
    def get_default_interface_class(cls):
        if cls._default_interface_class is None:
            raise GateImplementationError(
                f"This class has no _default_interface_class class attribute defined. "
            )
        return cls._default_interface_class

    @classmethod
    def get_user_info_default_values_interface(cls, **kwargs):
        # FIXME: not sure yet how to handle keep_data_in_memory
        #        because it is not a per-interface but per actor output parameter
        # defaults = {"keep_data_in_memory": cls.inherited_user_info_defaults["keep_data_in_memory"][0]}
        defaults = {}
        return defaults

    @classmethod
    def set_user_info_default_values_interface(cls, **kwargs):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.data_per_run = {}  # holds the data per run in memory
        self.merged_data = None  # holds the data merged from multiple runs in memory

    def __len__(self):
        return len(self.data_per_run)

    def get_run_indices(self, **kwargs):
        return [k for k, v in self.data_per_run.items() if v is not None]

    def set_write_to_disk(self, value, **kwargs):
        raise NotImplementedError

    def get_write_to_disk(self, **kwargs):
        raise NotImplementedError

    def set_output_filename(self, value, **kwargs):
        raise NotImplementedError

    def get_output_filename(self, **kwargs):
        raise NotImplementedError

    def get_active(self, **kwargs):
        # actor output is always active in its base implementation;
        # derived classes can implement this differently, as for example the ActorOutputUsingDataItemContainer class
        return True

    def set_active(self, value, **kwargs):
        if value is False:
            self.warn_user(
                f"You try to deactivate user output {self.name} "
                f"belonging to actor {self.belongs_to}, but this output cannot be deactivated. "
            )

    def get_item_suffix(self, **kwargs):
        return None

    def set_item_suffix(self, value, **kwargs):
        raise NotImplementedError

    @property
    def belongs_to_actor(self):
        if self.simulation is None:
            fatal(
                "Cannot determine the actor to which this output belongs. "
                "Probably, the actor has not yet been added to a simulation. "
            )
        return self.simulation.actor_manager.get_actor(self.belongs_to)

    def initialize(self):
        pass

    def _generate_auto_output_filename(self, **kwargs):
        return f"{self.name}_from_{self.belongs_to_actor.type_name.lower()}_{self.belongs_to_actor.name}.{self.default_suffix}"

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
                run_index = None  # remove warning from IDE
            return insert_suffix_before_extension(full_data_path, f"run{run_index}")

    def get_output_path(self, which="merged", **kwargs):
        # try to get the output_filename via 2 successive attempts
        # 1) a getter method if implemented (takes priority)
        # 2) directly via an attribute (fall-back)
        # If none of the two ways work, something is incorrectly implemented,
        # i.e. a developer's problem, not a user problem, and we raise a GateImplementationError
        try:
            output_filename = self.get_output_filename(**kwargs)
        except NotImplementedError:
            try:
                output_filename = getattr(self, "output_filename")
            except AttributeError:
                raise GateImplementationError(
                    f"Unable to get the output_filename "
                    f"in user_output {self.name} "
                    f"of actor {self.belongs_to_actor.name}."
                )
        # 'auto' means that the output_filename is automatically generated.
        if output_filename == "auto":
            output_filename = self._generate_auto_output_filename(**kwargs)
        if output_filename is None or output_filename == "":
            warning(
                f"No output_filename defined for user output '{self.name}' "
                f"of {self.belongs_to_actor.type_name} '{self.belongs_to_actor.name}'. "
                f"Therefore, get_output_path() returns None. "
            )
            return None
        else:
            return self._compose_output_path(which, output_filename)

    def get_output_path_as_string(self, **kwargs):
        return ensure_filename_is_str(self.get_output_path(**kwargs))

    def close(self):
        if self.keep_data_in_memory is False:
            self.data_per_run = {}
            self.merged_data = None
        super().close()

    def get_data(self, **kwargs):
        raise NotImplementedError("This is the base class. ")

    def store_data(self, *args, **kwargs):
        raise NotImplementedError("This is the base class. ")

    def write_data(self, *args, **kwargs):
        raise NotImplementedError("This is the base class. ")

    def write_data_if_requested(self, **kwargs):
        raise NotImplementedError("This is the base class. ")

    def load_data(self, which):
        raise NotImplementedError(
            f"Your are calling this method from the base class {type(self).__name__}, "
            f"but it should be implemented in the specific derived class"
        )


class ActorOutputUsingDataItemContainer(ActorOutputBase):
    # hints for IDE
    merge_data_after_simulation: bool
    keep_data_per_run: bool
    data_item_config: Optional[Box]

    user_info_defaults = {
        "merge_data_after_simulation": (
            True,
            {
                "doc": "In case the simulation has multiple runs, should results from separate runs be merged?"
            },
        ),
        "keep_data_per_run": (
            False,
            {
                "doc": "In case the simulation has multiple runs, should separate results per run be kept?"
            },
        ),
    }

    # this intermediate base class defines a class attribute data_container_class,
    # but leaves it as None. Specific classes need to set it to the correct class or tuple of classes
    data_container_class = None
    _default_interface_class = UserInterfaceToActorOutputUsingDataItemContainer
    _default_data_item_config = None

    @classmethod
    def get_user_info_default_values_interface(cls, item=0, **kwargs):
        defaults = super().get_user_info_default_values_interface(**kwargs)
        for k, v in cls._default_data_item_config[item].items():
            defaults[k] = v
        return defaults

    @classmethod
    def set_user_info_default_values_interface(cls, item=0, **kwargs):
        # pick up the defaults to be stored in the default data item config dictionary
        # and let the base class handle the rest
        known_defaults = list(cls._default_data_item_config[item].keys())
        for k in known_defaults:
            if k in kwargs:
                cls._default_data_item_config[item][k] = kwargs.pop(k)
        super().set_user_info_default_values_interface(**kwargs)

    @classmethod
    def __process_this__(cls):
        super().__process_this__()
        # we need to fill the _default_data_item_config of this class
        # depending on the container classes it handles
        if cls.data_container_class is not None:
            cls._default_data_item_config = {}
            # ask the container class which data item (including aliases and effective names)
            # it handles so that we can corerctly populate the defaults
            for k in cls.data_container_class.__get_data_item_names__():
                if isinstance(k, (int,)):
                    suffix = f"item{k}"
                else:
                    suffix = k
                cls._default_data_item_config[k] = {
                    "output_filename": "auto",
                    "write_to_disk": True,
                    "active": False,
                    "suffix": suffix,
                }
            # if there is only one item, set suffix to None
            # because we do not want to append anything to the output_filename in this case
            # and activate the output
            if len(cls._default_data_item_config) == 1:
                list(cls._default_data_item_config.values())[0]["suffix"] = None
                list(cls._default_data_item_config.values())[0]["active"] = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_item_config = copy.deepcopy(self._default_data_item_config)

    def initialize_cpp_parameters(self):
        # Create structs on C++ side for this actor output
        # This struct is only needed by actors that handle output written in C++.
        # But it does not hurt to populate the info in C++ regardless of the actor
        # The output path can also be (re-)set by the specific actor in
        # StartSimulation or BeginOfRunActionMasterThread, if needed
        items = self._collect_item_identifiers("all")
        for h in items:
            identifier = f"{self.name}_{h}"
            self.belongs_to_actor.AddActorOutputInfo(identifier)
            self.belongs_to_actor.SetWriteToDisk(
                identifier, self.get_write_to_disk(item=h)
            )
            self.belongs_to_actor.SetOutputPath(
                identifier, self.get_output_path_as_string(item=h)
            )

    def to_dictionary(self):
        d = super().to_dictionary()
        d["data_item_config"] = self.data_item_config
        return d

    def from_dictionary(self, d):
        super().from_dictionary(d)
        self.data_item_config = d["data_item_config"]

    def _fatal_unknown_item(self, item):
        fatal(
            f"Unknown item {item}. Known items are {list(self.data_item_config.keys())}."
        )

    # override methods:
    def set_write_to_disk(self, value, item=0):
        items = self._collect_item_identifiers(item)
        for i in items:
            self.data_item_config[i]["write_to_disk"] = bool(value)

    def get_write_to_disk(self, item=0):
        items = self._collect_item_identifiers(item)
        return any([self.data_item_config[k]["write_to_disk"] is True for k in items])

    def set_active(self, value, item=0):
        items = self._collect_item_identifiers(item)
        for i in items:
            self.data_item_config[i]["active"] = bool(value)

    def get_active(self, item=0):
        if item == "any":
            item = "all"
        items = self._collect_item_identifiers(item)
        return any([self.data_item_config[k]["active"] is True for k in items])

    def set_output_filename(self, value, item=0):
        if item == "all":
            for k, v in self.data_item_config.items():
                self.set_output_filename(self._insert_item_suffix(value, k), item=k)
        else:
            try:
                self.data_item_config[item]["output_filename"] = str(value)
            except KeyError:
                self._fatal_unknown_item(item)

    def get_output_filename(self, item=0):
        if item == "all":
            return dict(
                [(k, self.get_output_filename(item=k)) for k in self.data_item_config]
            )
        else:
            try:
                return self.data_item_config[item]["output_filename"]
            except KeyError:
                self._fatal_unknown_item(item)

    def get_item_suffix(self, item=0, **kwargs):
        if item == "all":
            return dict(
                [(k, self.get_item_suffix(item=k)) for k in self.data_item_config]
            )
        else:
            try:
                # FIXME: the .get() method implicitly defines a default value, but it should not. Is this a workaround?
                # return self.data_item_config[item].get("suffix", str(item))
                return self.data_item_config[item]["suffix"]
            except KeyError:
                self._fatal_unknown_item(item)

    def set_item_suffix(self, value, item=0, **kwargs):
        items = self._collect_item_identifiers(item)
        if len(items) > 1:
            fatal("You can set the item suffix only for one item at a time. ")
        self.data_item_config[item]["suffix"] = value

    def _generate_auto_output_filename(self, item=0):
        # try to get a suffix from the data item config dictionary
        # and fall back to the item name (or index) in case no suffix is found
        output_filename = super()._generate_auto_output_filename()
        return self._insert_item_suffix(output_filename, item)

    def _insert_item_suffix(self, output_filename, item):
        suffix = self.data_item_config[item].get("suffix", str(item))
        if suffix is not None:
            output_filename = insert_suffix_before_extension(output_filename, suffix)
        return output_filename

    def _collect_item_identifiers(self, item):
        if item == "all":
            items = list(self.data_item_config.keys())
        elif isinstance(item, (tuple, list)):
            items = item
        else:
            items = [item]
        if not all([i in self.data_item_config for i in items]):
            fatal(
                f"Unknown items. Requested items are: {items}. "
                f"Known items are {list(self.data_item_config.keys())}."
            )
        return items

    def get_output_path(
        self, which="merged", item=0, always_return_dict=False, **kwargs
    ):
        return_dict = {}
        for i in self._collect_item_identifiers(item):
            return_dict[i] = super().get_output_path(which=which, item=i)
        if len(return_dict) > 1 or always_return_dict is True:
            return return_dict
        else:
            return list(return_dict.values())[0]

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

    def get_data(self, which="merged", item=0):
        container = self.get_data_container(which)
        if container is None:
            return None
        else:
            return container.get_data(item=item)

    def store_data(self, which, *data):
        """data can be either the user data to be wrapped into a DataContainer class or
        an already wrapped DataContainer class.
        """

        if isinstance(data, self.data_container_class):
            data_container = data
            data_container.belongs_to = self
        else:
            data_container = self.data_container_class(belongs_to=self, data=data)
        # FIXME: use store_data if target data exists, otherwise create new container
        if which == "merged":
            self.merged_data = data_container
        else:
            try:
                run_index = int(which)  # might be a run_index
            except ValueError:
                fatal(
                    f"Invalid argument 'which' in store_data() method of ActorOutput {self.name}. "
                    f"Allowed values are: 'merged' or a valid run_index. "
                )
                run_index = None  # avoid IDE warning
            self.data_per_run[run_index] = data_container

    def store_meta_data(self, which, **meta_data):
        """data can be either the user data to be wrapped into a DataContainer class or
        an already wrapped DataContainer class.
        """

        data = self.get_data_container(which)
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
                ri = None  # avoid IDE warning
            data = [self.data_per_run[ri]]
            identifiers = [ri]
        if return_identifier is True:
            return data, identifiers
        else:
            return data

    def write_data(self, which="all", item="all", **kwargs):
        if which == "all_runs":
            for k in self.data_per_run.keys():
                self.write_data(which=k, item=item, **kwargs)
        elif which == "all":
            self.write_data(which="all_runs", item=item, **kwargs)
            self.write_data(which="merged", item=item, **kwargs)
        else:
            data = self.get_data_container(which)
            if data is not None:
                items = self._collect_item_identifiers(item)
                for i in items:
                    data.write(
                        self.get_output_path(which=which, item=i, **kwargs), item=i
                    )

    def write_data_if_requested(self, which="all", item="all", **kwargs):
        items = [
            i
            for i in self._collect_item_identifiers(item)
            if self.get_write_to_disk(item=i) is True
            and self.get_active(item=i) is True
            # FIXME: the active is True check should not be here. self.write_data() should handle that
        ]
        self.write_data(which=which, item=items)

    def merge_data_from_runs(self):
        self.merged_data = merge_data(list(self.data_per_run.values()))

    def end_of_run(self, run_index):
        if self.merge_data_after_simulation is True:
            self.merged_data.inplace_merge_with(self.data_per_run[run_index])
        if self.keep_data_per_run is False:
            self.data_per_run.pop(run_index)

    def start_of_simulation(self, **kwargs):
        if self.merge_data_after_simulation is True:
            self.merged_data = self.data_container_class(belongs_to=self)

    def end_of_simulation(self, item="all", **kwargs):
        try:
            self.write_data_if_requested(item="all", **kwargs)
        except NotImplementedError:
            raise GateImplementationError(
                "Unable to run end_of_simulation "
                f"in user_output {self.name} of actor {self.belongs_to_actor.name}"
                f"because the class does not implement a write_data_if_requested() "
                f"and/or write_data() method. "
                f"A developer needs to fix this. "
            )


class ActorOutputImage(ActorOutputUsingDataItemContainer):
    _default_interface_class = UserInterfaceToActorOutputImage

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
                    image_data_container = None  # avoid IDE warning
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


class ActorOutputSingleMeanImage(ActorOutputImage):
    data_container_class = SingleMeanItkImage


class ActorOutputSingleImageWithVariance(ActorOutputImage):
    data_container_class = SingleItkImageWithVariance


class ActorOutputQuotientImage(ActorOutputImage):
    data_container_class = QuotientItkImage


class ActorOutputQuotientMeanImage(ActorOutputImage):
    data_container_class = QuotientMeanItkImage


class ActorOutputRoot(ActorOutputBase):
    # hints for IDE
    output_filename: str
    write_to_disk: bool
    keep_data_in_memory: bool

    user_info_defaults = {
        "output_filename": (
            "auto",
            {
                "doc": "Filename for the data represented by this actor output. "
                "Relative paths and filenames are taken "
                "relative to the global simulation output folder "
                "set via the Simulation.output_dir option. ",
            },
        ),
        "write_to_disk": (
            True,
            {
                "doc": "Should the output be written to disk, or only kept in memory? ",
            },
        ),
        "keep_data_in_memory": (
            False,
            {
                "doc": "Should the data be kept in memory after the end of the simulation? "
                "Otherwise, it is only stored on disk and needs to be re-loaded manually. "
                "Careful: Large data structures like a phase space need a lot of memory. \n"
                "Warning: Feature not supported for ROOT output yet. The options is forced to False. ",
                "override": True,
                "read_only": True,
            },
        ),
    }

    default_suffix = "root"

    @classmethod
    def get_user_info_default_values_interface(cls, **kwargs):
        defaults = super().get_user_info_default_values_interface(**kwargs)
        for k in ["output_filename", "write_to_disk"]:
            defaults[k] = cls.inherited_user_info_defaults[k][0]
        return defaults

    @classmethod
    def set_user_info_default_values_interface(cls, **kwargs):
        for k in ["output_filename", "write_to_disk"]:
            if k in kwargs:
                current_default_tuple = cls.inherited_user_info_defaults[k]
                cls.inherited_user_info_defaults[k] = (
                    kwargs.pop(k),
                    current_default_tuple[1],
                )
        super().set_user_info_default_values_interface(**kwargs)

    def get_output_path(self, *args, **kwargs):
        if "which" in kwargs and kwargs["which"] != "merged":
            self.warn_user(
                "Currently, GATE 10 only stores cumulative ROOT output per simulation ('merged'), "
                "not data per run. Showing you the path to the ROOT file with cumulative data."
            )
        return super().get_output_path(which="merged")

    def initialize(self):
        # Warning, for the moment, MT and root output does not work on windows machine
        if sys.platform.startswith("nt"):
            if g4.IsMultithreadedApplication():
                fatal(
                    f"Sorry Multithreading and Root output does not work (yet) on windows architecture."
                    f"You can run the simulation in single-threaded mode of switch to linux/max."
                )

        # for ROOT output, not output_filename means no output to disk (legacy Gate 9 behavior)
        if self.output_filename == "" or self.output_filename is None:
            self.write_to_disk = False
        self.initialize_cpp_parameters()
        super().initialize()

    def initialize_cpp_parameters(self):
        self.belongs_to_actor.AddActorOutputInfo(self.name)
        self.belongs_to_actor.SetWriteToDisk(self.name, self.write_to_disk)
        if self.output_filename == "" or self.output_filename is None:
            # this test avoid a warning in get_output_path when it is None
            self.belongs_to_actor.SetOutputPath(self.name, "None")
        else:
            self.belongs_to_actor.SetOutputPath(
                self.name, self.get_output_path_as_string()
            )


process_cls(ActorOutputBase)
process_cls(ActorOutputUsingDataItemContainer)
process_cls(ActorOutputImage)
process_cls(ActorOutputSingleImage)
process_cls(ActorOutputSingleMeanImage)
process_cls(ActorOutputSingleImageWithVariance)
process_cls(ActorOutputQuotientImage)
process_cls(ActorOutputQuotientMeanImage)
process_cls(ActorOutputRoot)
