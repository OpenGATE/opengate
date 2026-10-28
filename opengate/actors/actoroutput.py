import copy
import inspect
import sys
from typing import Optional
from pathlib import Path

import opengate_core as g4
from box import Box

from ..base import GateObject, process_cls
from ..exception import (
    GateDeprecationError,
    GateImplementationError,
    GateMergeError,
    fatal,
    warning,
)
from ..image import create_3d_image_of_histogram
from ..utility import ensure_filename_is_str, insert_suffix_before_extension
from .dataitems import (
    QuotientItkImage,
    QuotientMeanItkImage,
    SingleRootTree,
    SingleItkImage,
    SingleItkImageWithVariance,
    SingleMeanItkImage,
    StatisticsItemContainer,
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

    def __str__(self):
        """Forward string conversion to the underlying actor output."""
        return str(self._user_output)

    def __repr__(self):
        """Forward the debug representation to the underlying actor output."""
        return repr(self._user_output)

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
        return self._user_output.get_data(which=which, **kwargs)

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
    def is_container_output(cls):
        return False

    @classmethod
    def is_root_output(cls):
        return False

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

    def _find_interface_names_for_this_output(self):
        try:
            actor = self.belongs_to_actor
        except Exception:
            return []
        interface_names = []
        for interface_name, interface in actor.interfaces_to_user_output.items():
            if getattr(interface, "user_output_name", None) == self.name:
                interface_names.append(interface_name)
        return interface_names

    def _format_raw_output_deprecation_message(
        self, property_name, explicit_setter, explicit_getter
    ):
        interface_names = self._find_interface_names_for_this_output()
        if len(interface_names) == 1:
            interface_hint = (
                f"If your actor variable is called my_actor, use "
                f"`my_actor.{interface_names[0]}.{property_name}` instead."
            )
        elif len(interface_names) > 1:
            joined_interfaces = ", ".join(
                [
                    f"`my_actor.{interface_name}.{property_name}`"
                    for interface_name in interface_names
                ]
            )
            interface_hint = (
                f"This output is exposed through multiple actor interfaces. "
                f"If your actor variable is called my_actor, use one of: {joined_interfaces}."
            )
        else:
            interface_hint = (
                "No matching actor-output interface could be identified automatically "
                "for this raw output object."
            )

        return (
            f"Direct raw ActorOutput access via `actor.user_output['{self.name}'].{property_name}` "
            f"is deprecated. This convenience property used to look like a simple "
            f"user_info entry, but its authoritative state now lives in the "
            f"container-backed item configuration.\n"
            f"{interface_hint}\n"
            f"If you intentionally work with the raw ActorOutput object, use "
            f"`{explicit_setter}` for writes and `{explicit_getter}` for reads."
        )

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

    def resolve_and_validate_config(self, context=None):
        if context == "split_preparation":
            self._warn_if_absolute_output_filenames()

    def _warn_if_absolute_output_filenames(self):
        try:
            output_filename = self.get_output_filename()
        except NotImplementedError:
            return
        if output_filename in (None, "", "auto"):
            return
        try:
            output_path = Path(output_filename)
        except TypeError:
            return
        if output_path.is_absolute():
            self.warn_user(
                f"Actor output '{self.name}' uses the absolute output path "
                f"'{output_path}'. Absolute output paths can cause split-job "
                "output merging to fail."
            )

    def initialize_cpp_parameters(self):
        pass

    def initialize(self):
        # Actor outputs should have been resolved already during the simulation
        # config phase. At runtime, initialize() is limited to registering the
        # already-resolved output metadata on the actor's C++ side.
        self.initialize_cpp_parameters()

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

    def reset_data(self):
        self.merged_data = None
        self.data_per_run = {}

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

    def load_data(self, which, **kwargs):
        raise NotImplementedError(
            f"Your are calling this method from the base class {type(self).__name__}, "
            f"but it should be implemented in the specific derived class"
        )

    def merge_data_from_actor_output(self, *actor_output, **kwargs):
        raise NotImplementedError("This is the base class. ")

    def plan_merge(self, mode="as_configured"):
        return {
            "actor_name": self.belongs_to_actor.name,
            "output_name": self.name,
            "output_type": type(self).__name__,
            "mergeable": False,
            "is_root_output": self.is_root_output(),
            "merge_coordinator": "root" if self.is_root_output() else "standard",
            "contributions": [],
        }

    def execute_merge(self, source_output, context=None):
        return

    def finalize_merge(self, context=None):
        return


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
    def is_container_output(cls):
        return True

    @classmethod
    def get_user_info_default_values_interface(cls, item=0, **kwargs):
        defaults = super().get_user_info_default_values_interface(**kwargs)
        item = cls.data_container_class.normalize_item_identifier(item)
        for k, v in cls._default_data_item_config[item].items():
            defaults[k] = v
        return defaults

    @classmethod
    def set_user_info_default_values_interface(cls, item=0, **kwargs):
        # pick up the defaults to be stored in the default data item config dictionary
        # and let the base class handle the rest
        item = cls.data_container_class.normalize_item_identifier(item)
        known_defaults = list(cls._default_data_item_config[item].keys())
        for k in known_defaults:
            if k in kwargs:
                cls._default_data_item_config[item][k] = kwargs.pop(k)
        super().set_user_info_default_values_interface(**kwargs)

    @classmethod
    def _build_default_data_item_config(cls):
        if cls.data_container_class is None:
            return None
        return cls.data_container_class.build_default_data_item_config()

    @classmethod
    def __process_this__(cls):
        super().__process_this__()
        if cls.data_container_class is not None:
            # The container class is the authoritative place that knows which
            # primary and derived items it exposes. Actor outputs only consume
            # that declaration to build their per-item configuration defaults.
            cls._default_data_item_config = cls._build_default_data_item_config()

    def __init__(self, *args, **kwargs):
        item_config_overrides = kwargs.pop("item_config_overrides", None)
        super().__init__(*args, **kwargs)
        self.data_item_config = copy.deepcopy(self._default_data_item_config)
        self._apply_item_config_overrides(item_config_overrides)

    def _build_plan_merge_as_configured_output_plan(self):
        contributions = []
        primary_item_identifiers = (
            self.data_container_class.get_primary_item_identifiers()
        )
        run_scopes = []
        if self.keep_data_per_run:
            run_scopes.extend(
                [
                    {"source_scope": run_index, "target_scope": run_index}
                    for run_index in range(len(self.simulation.run_timing_intervals))
                ]
            )
        if self.merge_data_after_simulation:
            run_scopes.append({"source_scope": "merged", "target_scope": "merged"})

        for item_identifier in primary_item_identifiers:
            item_is_active = self.get_active(item=item_identifier)
            item_written_to_disk = self.get_write_to_disk(item=item_identifier)
            output_filename = self.get_output_filename(item=item_identifier)
            mergeable = bool(item_is_active and item_written_to_disk)

            for run_scope in run_scopes:
                source_scope = run_scope["source_scope"]
                target_scope = run_scope["target_scope"]
                contributions.append(
                    {
                        "actor_name": self.belongs_to_actor.name,
                        "output_name": self.name,
                        "item_identifier": item_identifier,
                        "source_scope": source_scope,
                        "target_scope": target_scope,
                        "output_filename": output_filename,
                        "output_path": (
                            None
                            if output_filename is None
                            else str(
                                self.get_output_path(
                                    which=source_scope,
                                    item=item_identifier,
                                )
                            )
                        ),
                        "expected_on_disk": bool(item_written_to_disk),
                        "mergeable": mergeable,
                    }
                )

        return {
            "actor_name": self.belongs_to_actor.name,
            "output_name": self.name,
            "output_type": type(self).__name__,
            "mergeable": any(
                contribution["mergeable"] for contribution in contributions
            ),
            "is_root_output": self.is_root_output(),
            "merge_coordinator": "standard",
            "contributions": contributions,
        }

    def plan_merge(self, mode="as_configured"):
        if mode != "as_configured":
            raise NotImplementedError(
                f"Actor output planning mode '{mode}' is not implemented yet for "
                f"{type(self).__name__}."
            )
        return self._build_plan_merge_as_configured_output_plan()

    def execute_merge(self, source_output, context=None):
        if not source_output.is_container_output():
            raise GateMergeError(
                f"Cannot execute merge of non-container output '{source_output.name}' "
                f"into container output '{self.name}'."
            )
        if context is None:
            raise GateMergeError(
                f"Missing output-level merge context while merging output '{self.name}'."
            )
        if not hasattr(context, "get_contributions"):
            raise GateMergeError(
                "ActorOutput.execute_merge() expects an OutputMergeContextView."
            )

        load_mode = context.get_load_mode(default="rehydrated")
        contributions = context.get_contributions()

        # Jobs-merge treats per-run and merged/cumulative payloads as distinct
        # slots. Source run slots merge directly into target run slots, while
        # source merged payloads merge directly into the target merged slot.
        # The jobs-merge workflow must not rebuild merged output from
        # ``data_per_run`` because merged-only child outputs are legitimate.
        for contribution in contributions:
            if contribution.get("mergeable") is not True:
                continue
            source_scope = contribution.get("source_scope")
            target_scope = contribution.get("target_scope")
            item_identifier = contribution.get("item_identifier")
            try:
                source_output.load_data(
                    which=source_scope,
                    item=item_identifier,
                    load_mode=load_mode,
                )
                self.merge_data_from_output(
                    source_output,
                    which_source=source_scope,
                    which_target=target_scope,
                )
            finally:
                source_output.clear_data(which=source_scope, item=item_identifier)

    def finalize_merge(self, context=None):
        if self.is_root_output():
            # ROOT outputs are finalized by the RootMergeCoordinator because
            # several actor outputs may contribute distinct trees to the same
            # physical ROOT file.
            return
        has_per_run_data = len(self.data_per_run) > 0
        has_merged_data = self.merged_data is not None
        if not has_per_run_data and not has_merged_data:
            return
        # In the jobs-merge workflow, cumulative/merged payloads must already
        # have been constructed explicitly during execute_merge(). Do not
        # synthesize them from ``data_per_run`` here because merged-only child
        # outputs are legitimate and would otherwise be dropped.
        self.write_data_if_requested(which="all")

    @property
    def write_to_disk(self):
        raise GateDeprecationError(
            self._format_raw_output_deprecation_message(
                "write_to_disk",
                f"my_actor.user_output['{self.name}'].set_write_to_disk(VALUE, item=...)",
                f"my_actor.user_output['{self.name}'].get_write_to_disk(item=...)",
            )
        )

    @write_to_disk.setter
    def write_to_disk(self, value):
        raise GateDeprecationError(
            self._format_raw_output_deprecation_message(
                "write_to_disk",
                f"my_actor.user_output['{self.name}'].set_write_to_disk(VALUE, item=...)",
                f"my_actor.user_output['{self.name}'].get_write_to_disk(item=...)",
            )
        )

    @property
    def output_filename(self):
        raise GateDeprecationError(
            self._format_raw_output_deprecation_message(
                "output_filename",
                f"my_actor.user_output['{self.name}'].set_output_filename(VALUE, item=...)",
                f"my_actor.user_output['{self.name}'].get_output_filename(item=...)",
            )
        )

    @output_filename.setter
    def output_filename(self, value):
        raise GateDeprecationError(
            self._format_raw_output_deprecation_message(
                "output_filename",
                f"my_actor.user_output['{self.name}'].set_output_filename(VALUE, item=...)",
                f"my_actor.user_output['{self.name}'].get_output_filename(item=...)",
            )
        )

    @property
    def active(self):
        raise GateDeprecationError(
            self._format_raw_output_deprecation_message(
                "active",
                f"my_actor.user_output['{self.name}'].set_active(VALUE, item=...)",
                f"my_actor.user_output['{self.name}'].get_active(item=...)",
            )
        )

    @active.setter
    def active(self, value):
        raise GateDeprecationError(
            self._format_raw_output_deprecation_message(
                "active",
                f"my_actor.user_output['{self.name}'].set_active(VALUE, item=...)",
                f"my_actor.user_output['{self.name}'].get_active(item=...)",
            )
        )

    @property
    def suffix(self):
        raise GateDeprecationError(
            self._format_raw_output_deprecation_message(
                "suffix",
                f"my_actor.user_output['{self.name}'].set_item_suffix(VALUE, item=...)",
                f"my_actor.user_output['{self.name}'].get_item_suffix(item=...)",
            )
        )

    @suffix.setter
    def suffix(self, value):
        raise GateDeprecationError(
            self._format_raw_output_deprecation_message(
                "suffix",
                f"my_actor.user_output['{self.name}'].set_item_suffix(VALUE, item=...)",
                f"my_actor.user_output['{self.name}'].get_item_suffix(item=...)",
            )
        )

    def _normalize_item_identifier(self, item):
        try:
            return self.data_container_class.normalize_item_identifier(item)
        except GateImplementationError:
            self._fatal_unknown_item(item)

    def _warn_if_absolute_output_filenames(self):
        try:
            output_filenames = self.get_output_filename(item="all")
        except NotImplementedError:
            return
        for item_identifier, output_filename in output_filenames.items():
            if output_filename in (None, "", "auto"):
                continue
            try:
                output_path = Path(output_filename)
            except TypeError:
                continue
            if output_path.is_absolute():
                self.warn_user(
                    f"Actor output '{self.name}' for item '{item_identifier}' "
                    f"uses the absolute output path '{output_path}'. Absolute "
                    "output paths can cause split-job output merging to fail."
                )

    def _apply_item_config_overrides(self, item_config_overrides):
        if item_config_overrides is None:
            return
        # Apply per-output semantic overrides such as suffixes. The container
        # defines the generic item surface; the concrete actor output instance
        # refines it for this specific use in a given actor.
        for item_identifier, item_config in item_config_overrides.items():
            normalized_identifier = self._normalize_item_identifier(item_identifier)
            for key, value in item_config.items():
                if key not in self.data_item_config[normalized_identifier]:
                    raise GateImplementationError(
                        f"Unknown data item config key '{key}' for item "
                        f"{normalized_identifier!r} in actor output {self.name}. "
                        f"Known keys are "
                        f"{list(self.data_item_config[normalized_identifier].keys())}."
                    )
                self.data_item_config[normalized_identifier][key] = value

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
        # Container-backed actor outputs keep per-item persistence settings in
        # ``data_item_config``. The legacy raw convenience fields such as
        # ``output_filename`` and ``write_to_disk`` are intentionally deprecated
        # on the ActorOutput object itself, so deserialization must not route
        # through those raw property setters.
        d_base = copy.deepcopy(d)
        for deprecated_raw_key in (
            "output_filename",
            "write_to_disk",
            "active",
            "suffix",
        ):
            d_base["user_info"].pop(deprecated_raw_key, None)
        super().from_dictionary(d_base)
        self.data_item_config = self._restore_data_item_config_from_dictionary(
            d["data_item_config"]
        )

    def _fatal_unknown_item(self, item):
        fatal(
            f"Unknown item {item}. Known items are {list(self.data_item_config.keys())}."
        )

    def _restore_data_item_config_from_dictionary(self, data_item_config):
        """Restore the canonical key types after JSON deserialization.

        JSON object keys are always strings, but internally some data item
        identifiers are integers (e.g. 0, 1) while others are named aliases
        such as 'variance' or 'uncertainty'. Use the class defaults as the
        authoritative source for which key types should be restored.
        """

        if self._default_data_item_config is None:
            return data_item_config

        restored_config = {}
        for key, value in data_item_config.items():
            restored_key = self.data_container_class.normalize_item_identifier(key)
            restored_config[restored_key] = value
        return restored_config

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
            item = self._normalize_item_identifier(item)
            try:
                # Preserve ``None`` as a sentinel meaning "no output file"
                # instead of stringifying it to ``"None"``. Several existing
                # digitizer helpers still set output_filename=None explicitly to
                # disable ROOT persistence, and config resolution relies on a
                # real None value to switch write_to_disk off.
                if value is None:
                    self.data_item_config[item]["output_filename"] = None
                else:
                    self.data_item_config[item]["output_filename"] = str(value)
            except KeyError:
                self._fatal_unknown_item(item)

    def get_output_filename(self, item=0):
        if item == "all":
            return dict(
                [(k, self.get_output_filename(item=k)) for k in self.data_item_config]
            )
        else:
            item = self._normalize_item_identifier(item)
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
            item = self._normalize_item_identifier(item)
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
        self.data_item_config[items[0]]["suffix"] = value

    def _generate_auto_output_filename(self, item=0):
        # try to get a suffix from the data item config dictionary
        # and fall back to the item name (or index) in case no suffix is found
        output_filename = super()._generate_auto_output_filename()
        return self._insert_item_suffix(output_filename, item)

    def _insert_item_suffix(self, output_filename, item):
        item = self._normalize_item_identifier(item)
        suffix = self.data_item_config[item].get("suffix", str(item))
        if suffix is not None:
            output_filename = insert_suffix_before_extension(output_filename, suffix)
        return output_filename

    def _collect_item_identifiers(self, item):
        if item == "all":
            items = list(self.data_item_config.keys())
        elif isinstance(item, (tuple, list)):
            items = [self._normalize_item_identifier(i) for i in item]
        else:
            items = [self._normalize_item_identifier(item)]
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

    def reset_data(self):
        # Delegate resets to data containers where available so actor outputs
        # can clear their in-memory state symmetrically before reloading or
        # after importing from other actors.
        try:
            if self.merged_data is not None:
                self.merged_data.reset_data()
            for v in self.data_per_run.values():
                if v is not None:
                    v.reset_data()
        except (NotImplementedError, AttributeError):
            super().reset_data()

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
        raise GateDeprecationError(
            "ActorOutputUsingDataItemContainer.store_meta_data() is temporarily "
            "disabled on purpose. Origin: sample counting is being moved away "
            "from the generic meta_data dictionary toward explicit data-item "
            "capabilities. Use a dedicated API such as set_number_of_samples() "
            "instead."
        )

    def set_number_of_samples(self, which, number_of_samples, item="all"):
        data_container = self.ensure_data_container(which)
        data_container.set_number_of_samples(
            number_of_samples=number_of_samples,
            item=item,
        )

    def ensure_data_container(self, which):
        if which == "merged":
            if self.merged_data is None:
                self.merged_data = self.data_container_class(belongs_to=self)
            return self.merged_data
        try:
            run_index = int(which)
        except ValueError:
            fatal(
                f"Invalid argument 'which' in ensure_data_container() method of "
                f"ActorOutput {self.name}. Allowed values are: 'merged' or a valid "
                f"run_index. "
            )
        if run_index not in self.data_per_run or self.data_per_run[run_index] is None:
            self.data_per_run[run_index] = self.data_container_class(belongs_to=self)
        return self.data_per_run[run_index]

    def load_data(self, which, item="all", **kwargs):
        data_container = self.ensure_data_container(which)
        items = self._collect_item_identifiers(item)
        output_paths = self.get_output_path(
            which=which,
            item=items,
            always_return_dict=True,
            **kwargs,
        )
        if len(items) == 1:
            item_identifier = items[0]
            data_container.load_item(
                item=item_identifier,
                path=output_paths[item_identifier],
                **kwargs,
            )
        else:
            data_container.load_item(
                item="all",
                path={
                    item_identifier: output_paths[item_identifier]
                    for item_identifier in items
                },
                **kwargs,
            )

    def clear_data(self, which, item="all"):
        if which == "merged":
            data_container = self.merged_data
        else:
            try:
                run_index = int(which)
            except ValueError:
                fatal(
                    f"Invalid argument 'which' in clear_data() method of ActorOutput {self.name}. "
                    f"Allowed values are: 'merged' or a valid run_index. "
                )
            data_container = self.data_per_run.get(run_index)
        if data_container is None:
            return
        data_container.clear_items(item=item)

    def merge_data_from_output(self, source_output, which_source, which_target):
        source_container = source_output.get_data_container(which_source)
        if source_container is None:
            return
        target_container = self.ensure_data_container(which_target)
        target_container.inplace_merge_with(source_container)

    def in_place_merge(
        self, other_output, which_target, which_source, load_mode="live"
    ):
        if not other_output.is_container_output():
            raise GateMergeError(
                f"Cannot merge non-container output '{other_output.name}' into "
                f"container output '{self.name}'."
            )
        merge_item_identifiers = [
            item_identifier
            for item_identifier in other_output.data_container_class.get_primary_item_identifiers()
            if other_output.get_active(item=item_identifier)
            and other_output.get_write_to_disk(item=item_identifier)
        ]
        if load_mode == "rehydrated":
            merge_item_identifiers = [
                item_identifier
                for item_identifier in merge_item_identifiers
                if self.get_write_to_disk(item=item_identifier)
            ]
        if len(merge_item_identifiers) == 0:
            return
        try:
            other_output.load_data(
                which=which_source,
                item=merge_item_identifiers,
                load_mode=load_mode,
            )
            self.merge_data_from_output(
                other_output,
                which_source=which_source,
                which_target=which_target,
            )
        finally:
            other_output.clear_data(which=which_source, item=merge_item_identifiers)

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

    def merge_data_from_actor_output(
        self, *actor_output, discard_existing_data=True, **kwargs
    ):
        """Merge compatible actor outputs into this output.

        This is the in-memory merge contract used later by split-job merging:
        job orchestration should coordinate actor outputs, but the merge
        semantics themselves stay local to each ActorOutput class.
        """

        run_indices_to_import = set()
        for ao in actor_output:
            run_indices_to_import.update(ao.data_per_run.keys())

        for run_index in run_indices_to_import:
            data_to_import = [
                ao.data_per_run[run_index]
                for ao in actor_output
                if run_index in ao.data_per_run
            ]
            if discard_existing_data is False and run_index in self.data_per_run:
                data_to_import.append(self.data_per_run[run_index])
            self.data_per_run[run_index] = merge_data(data_to_import)

        merged_data_to_import = [
            ao.merged_data for ao in actor_output if ao.merged_data is not None
        ]
        if discard_existing_data is False and self.merged_data is not None:
            merged_data_to_import.append(self.merged_data)
        if len(merged_data_to_import) > 0:
            self.merged_data = merge_data(merged_data_to_import)


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


class ActorOutputImageOfHistogram(ActorOutputImage):
    def create_image_of_histograms(
        self, run_index, size, spacing, bins, origin=None, **kwargs
    ):
        if run_index not in self.data_per_run:
            self.data_per_run[run_index] = self.data_container_class(belongs_to=self)
        img = create_3d_image_of_histogram(size, spacing, bins, origin, **kwargs)
        self.data_per_run[run_index].set_data(img)


# concrete classes usable in Actors:
class ActorOutputSingleImage(ActorOutputImage):
    data_container_class = SingleItkImage


class ActorOutputSingleImageOfHistogram(ActorOutputImageOfHistogram):
    data_container_class = SingleItkImage


class ActorOutputSingleMeanImage(ActorOutputImage):
    data_container_class = SingleMeanItkImage


class ActorOutputSingleImageWithVariance(ActorOutputImage):
    data_container_class = SingleItkImageWithVariance


class ActorOutputQuotientImage(ActorOutputImage):
    data_container_class = QuotientItkImage


class ActorOutputQuotientMeanImage(ActorOutputImage):
    data_container_class = QuotientMeanItkImage


class ActorOutputStatisticsActor(ActorOutputUsingDataItemContainer):
    """Structured statistics output with semantic merge rules per entry."""

    _default_interface_class = UserInterfaceToActorOutputUsingDataItemContainer
    data_container_class = StatisticsItemContainer

    # hints for IDE
    encoder: str

    user_info_defaults = {
        "encoder": (
            "json",
            {
                "doc": "How should the output be encoded?",
                "allowed_values": ("json", "legacy"),
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        self.default_suffix = "json"
        super().__init__(*args, **kwargs)
        # Preserve the historical behavior of the statistics actor: defining
        # an output filename should imply persistence, but the mere existence
        # of an automatic default filename should not force writing to disk.
        self.set_write_to_disk(False)
        self.set_active(True)

    def execute_merge(self, source_output, context=None):
        super().execute_merge(source_output, context=context)
        if context is None or not hasattr(context, "get_contributions"):
            return

        # Multiple child-local run fragments can contribute to the same
        # original target run when a simulation is split by total active time.
        # For the statistics actor, the target per-run slot should still
        # represent exactly one original run, not the number of child pieces
        # that happened to cover it. Keep the per-run "runs" counter pinned to
        # one after merging all fragments into that slot; the later
        # merge_data_from_runs() step will then correctly reconstruct the total
        # number of original runs in the cumulative merged statistics output.
        # FIXME: Statistics merge semantics are special here. In general,
        # DataItem objects should stay agnostic of the run slot to which they
        # belong and ActorOutput should own the slotting. For the statistics
        # actor, however, the numerical merge rule for the "runs" entry depends
        # on that slot meaning: merging several child fragments into one
        # original target run should still result in runs=1. Keep this
        # workaround local to the statistics ActorOutput for now and revisit
        # later if the merge workflow grows a more explicit notion of slot
        # semantics.
        for contribution in context.get_contributions():
            target_scope = contribution.get("target_scope")
            if target_scope == "merged":
                continue
            target_container = self.data_per_run.get(int(target_scope))
            if target_container is None:
                continue
            target_item = target_container.get_data_item_object(0)
            if target_item is None or target_item.data is None:
                continue
            target_item.data.runs = 1

    @property
    def _stats_item(self):
        if self.merged_data is None:
            return None
        return self.merged_data.get_data_item_object(0)

    def resolve_and_validate_config(self, context=None):
        super().resolve_and_validate_config(context=context)
        if self.get_output_filename() not in ("", None, "auto"):
            self.set_write_to_disk(True)

    def get_processed_output(self):
        if self._stats_item is None:
            return {}
        return self._stats_item.get_processed_output()

    def __str__(self):
        if self._stats_item is None:
            return "No data found. "
        return str(self._stats_item)

    def write_data(self, which="all", item="all", **kwargs):
        # The base class implements recursive dispatch for ``which='all'`` and
        # ``which='all_runs'`` by calling ``self.write_data(...)`` again. Keep
        # the statistics-specific encoder stable across that recursion without
        # injecting it twice.
        kwargs.setdefault("encoder", self.encoder)
        super().write_data(which=which, item=item, **kwargs)


class ActorOutputRoot(ActorOutputUsingDataItemContainer):
    # hints for IDE
    output_filename: str
    write_to_disk: bool
    keep_data_in_memory: bool

    data_container_class = SingleRootTree

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
    def is_root_output(cls):
        return True

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

    def get_metadata_path(self):
        output_path = self.get_output_path(which="merged")
        if output_path is None:
            return None
        output_path = output_path.resolve()
        metadata_filename = (
            f"{output_path.stem}-{self.belongs_to_actor.name}-metadata.json"
        )
        return output_path.with_name(metadata_filename)

    def _get_requested_attribute_metadata(self):
        requested_attributes = None
        skipped_attributes = None
        if "attributes" in self.belongs_to_actor.user_info:
            attributes = self.belongs_to_actor.user_info["attributes"]
            if attributes is not None:
                requested_attributes = list(attributes)
        if "skip_attributes" in self.belongs_to_actor.user_info:
            attributes = self.belongs_to_actor.user_info["skip_attributes"]
            if attributes is not None:
                skipped_attributes = list(attributes)
        return requested_attributes, skipped_attributes

    def _ensure_run_id_requested_if_needed(self):
        if self.keep_data_per_run is not True:
            return

        # ROOT output that keeps data per run needs RunID to preserve run
        # identity after merging. Inject it during config resolution so the
        # runtime actor and the persisted metadata stay consistent even if the
        # user did not request it explicitly.
        if "attributes" in self.belongs_to_actor.user_info:
            requested_attributes = self.belongs_to_actor.user_info["attributes"]
            if requested_attributes is not None and "RunID" not in requested_attributes:
                self.belongs_to_actor.user_info["attributes"] = list(
                    requested_attributes
                ) + ["RunID"]
                self.warn_user(
                    f"Actor output '{self.name}' enabled keep_data_per_run=True; "
                    "adding 'RunID' to the requested ROOT attributes."
                )

        # A conflicting skip_attributes entry would silently defeat the
        # keep_data_per_run contract, so remove it here as part of the same
        # normalization step.
        if "skip_attributes" in self.belongs_to_actor.user_info:
            skipped_attributes = self.belongs_to_actor.user_info["skip_attributes"]
            if skipped_attributes is not None and "RunID" in skipped_attributes:
                self.belongs_to_actor.user_info["skip_attributes"] = [
                    attribute
                    for attribute in skipped_attributes
                    if attribute != "RunID"
                ]
                self.warn_user(
                    f"Actor output '{self.name}' enabled keep_data_per_run=True; "
                    "removing 'RunID' from skip_attributes."
                )

    def resolve_and_validate_config(self, context=None):
        super().resolve_and_validate_config(context=context)
        # Warning, for the moment, MT and root output does not work on windows machine
        if sys.platform.startswith("nt"):
            if g4.IsMultithreadedApplication():
                fatal(
                    f"Sorry Multithreading and Root output does not work (yet) on windows architecture."
                    f"You can run the simulation in single-threaded mode of switch to linux/max."
                )

        # For ROOT output, an empty or missing filename means "no ROOT file",
        # which keeps the legacy Gate 9 behavior. Use the explicit getter and
        # setter on the raw ActorOutput object rather than interface-style
        # attributes.
        output_filename = self.get_output_filename(item=0)
        if output_filename == "" or output_filename is None:
            self.set_write_to_disk(False, item=0)

        self._ensure_run_id_requested_if_needed()

    def initialize_cpp_parameters(self):
        self.belongs_to_actor.AddActorOutputInfo(self.name)
        write_to_disk = self.get_write_to_disk(item=0)
        output_filename = self.get_output_filename(item=0)
        self.belongs_to_actor.SetWriteToDisk(self.name, write_to_disk)
        if output_filename == "" or output_filename is None:
            # this test avoid a warning in get_output_path when it is None
            self.belongs_to_actor.SetOutputPath(self.name, "None")
        else:
            self.belongs_to_actor.SetOutputPath(
                self.name, self.get_output_path_as_string()
            )

    def _get_runtime_tree_names(self):
        tree_names = list(self.belongs_to_actor.GetOutputTreeNames(self.name))
        return tree_names if len(tree_names) > 0 else None

    def plan_merge(self, mode="as_configured"):
        if mode != "as_configured":
            raise NotImplementedError(
                f"Actor output planning mode '{mode}' is not implemented yet for "
                f"{type(self).__name__}."
            )

        output_filename = self.get_output_filename(item=0)
        item_written_to_disk = self.get_write_to_disk(item=0)
        contributions = []
        for run_index in range(len(self.simulation.run_timing_intervals)):
            contributions.append(
                {
                    "actor_name": self.belongs_to_actor.name,
                    "output_name": self.name,
                    "item_identifier": 0,
                    "source_scope": run_index,
                    "target_scope": run_index,
                    "output_filename": output_filename,
                    "output_path": (
                        None
                        if output_filename is None
                        else str(self.get_output_path(which="merged", item=0))
                    ),
                    "expected_on_disk": bool(item_written_to_disk),
                    "mergeable": bool(item_written_to_disk),
                }
            )

        return {
            "actor_name": self.belongs_to_actor.name,
            "output_name": self.name,
            "output_type": type(self).__name__,
            "mergeable": any(
                contribution["mergeable"] for contribution in contributions
            ),
            "is_root_output": True,
            "merge_coordinator": "root",
            "contributions": contributions,
        }

    def _get_runtime_tree_descriptors(self):
        tree_info = self.belongs_to_actor.GetOutputTreeInfo(self.name)
        if not tree_info:
            return None
        tree_descriptors = []
        for tree_name, branch_types in tree_info.items():
            tree_descriptors.append(
                {
                    "tree_name": tree_name,
                    "branches": dict(branch_types),
                }
            )
        return tree_descriptors if len(tree_descriptors) > 0 else None

    def merge_data_from_runs(self):
        # ROOT output is cumulative per simulation. Split-job merge collects
        # child contributions explicitly and materializes one merged tree at the
        # end instead of merging per-run in memory.
        return

    def load_data(self, which="merged", item="all", **kwargs):
        data_container = self.ensure_data_container("merged")
        data_container.load_item(
            item=0,
            path=self.get_output_path(which="merged"),
            metadata_path=self.get_metadata_path(),
            **kwargs,
        )

    def clear_data(self, which="merged", item="all"):
        if which != "merged":
            return
        super().clear_data(which="merged", item=item)

    def in_place_merge(
        self, other_output, which_target, which_source, load_mode="live"
    ):
        if type(self) is not type(other_output):
            raise GateMergeError(
                f"Cannot merge incompatible ROOT outputs '{other_output.name}' "
                f"into '{self.name}'."
            )
        if load_mode == "rehydrated" and (
            not self.get_write_to_disk(item=0)
            or not other_output.get_write_to_disk(item=0)
        ):
            return
        try:
            other_output.load_data(which="merged", load_mode=load_mode)
            target_container = self.ensure_data_container("merged")
            source_container = other_output.get_data_container("merged")
            target_item = target_container.get_data_item_object(0)
            source_item = source_container.get_data_item_object(0)
            if source_item.root_file_was_written() is False:
                self.warn_user(
                    f"Skipping ROOT merge contribution from actor output "
                    f"'{other_output.name}' because its persisted metadata "
                    "declares root_file_written=False."
                )
                return
            source_tree = source_item.get_single_tree_descriptor()
            # RunID is only required when the user expects ROOT output to
            # preserve per-run identity across the merged campaign. If the user
            # keeps only cumulative ROOT output, child trees can be merged in
            # split order without RunID because time ordering is already
            # preserved by the time-based split.
            if (
                self.keep_data_per_run is True
                and "RunID" not in source_tree["branches"]
            ):
                raise GateMergeError(
                    "Cannot merge ROOT output with keep_data_per_run=True because "
                    "the source tree does not contain a RunID branch."
                )
            if not target_item.has_root_meta_data():
                requested_attributes, skipped_attributes = (
                    self._get_requested_attribute_metadata()
                )
                target_item.set_root_meta_data(
                    {
                        "metadata_version": source_item.metadata_version,
                        "actor_name": self.belongs_to_actor.name,
                        "actor_type": self.belongs_to_actor.type_name,
                        "actor_output_name": self.name,
                        "root_output_path": str(
                            self.get_output_path(which="merged").resolve()
                        ),
                        "requested_attributes": requested_attributes,
                        "skipped_attributes": skipped_attributes,
                        "trees": source_item.root_meta_data["trees"],
                        "merge_sources": [],
                    }
                )
            target_item.register_merge_source(
                source_item,
                run_id_from=which_source,
                run_id_to=which_target,
            )
        finally:
            other_output.clear_data(which="merged", item=0)

    def execute_merge(self, source_output, context=None):
        if context is None:
            raise GateMergeError(
                f"Missing output-level merge context while merging ROOT output '{self.name}'."
            )
        if not hasattr(context, "get_contributions"):
            raise GateMergeError(
                "ActorOutputRoot.execute_merge() expects an OutputMergeContextView."
            )
        load_mode = context.get_load_mode(default="rehydrated")
        contributions = context.get_contributions()

        for contribution in contributions:
            if contribution.get("mergeable") is not True:
                continue
            source_scope = contribution.get("source_scope")
            target_scope = contribution.get("target_scope")
            if source_scope == "merged":
                continue
            self.in_place_merge(
                source_output,
                which_target=target_scope,
                which_source=source_scope,
                load_mode=load_mode,
            )

    def write_data(self, which="all", item="all", **kwargs):
        if which == "all_runs":
            return
        if which == "all":
            which = "merged"
        if which != "merged":
            self.warn_user(
                "ROOT output can only be written for the cumulative merged result. "
                f"Ignoring request to write '{which}'."
            )
            return
        data_container = self.get_data_container("merged")
        if data_container is None:
            return
        data_container.write(
            self.get_output_path(which="merged"),
            item=0,
            metadata_path=self.get_metadata_path(),
            **kwargs,
        )

    def store_runtime_metadata(self):
        if not self.get_write_to_disk(item=0):
            return
        output_path = self.get_output_path(which="merged")
        if output_path is None:
            return
        output_path = output_path.resolve()
        requested_attributes, skipped_attributes = (
            self._get_requested_attribute_metadata()
        )
        data_container = self.ensure_data_container("merged")
        data_item = data_container.get_data_item_object(0)
        if not output_path.exists():
            # Legitimate empty ROOT output currently leaves no ROOT file on
            # disk. Persist minimal metadata anyway so later rehydrated merge
            # logic can distinguish "empty contribution" from "broken child".
            data_item.capture_empty_runtime_metadata(
                output_path,
                actor_name=self.belongs_to_actor.name,
                actor_type=self.belongs_to_actor.type_name,
                actor_output_name=self.name,
                requested_attributes=requested_attributes,
                skipped_attributes=skipped_attributes,
            )
            metadata_path = self.get_metadata_path()
            data_item.save_root_metadata(metadata_path)
            self.warn_user(
                f"Actor output '{self.name}' was configured to write ROOT data, "
                f"but no ROOT file was produced. Writing minimal metadata with "
                f"root_file_written=False to '{metadata_path}'."
            )
            return
        data_item.capture_runtime_metadata(
            output_path,
            actor_name=self.belongs_to_actor.name,
            actor_type=self.belongs_to_actor.type_name,
            actor_output_name=self.name,
            tree_descriptors=self._get_runtime_tree_descriptors(),
            tree_names=self._get_runtime_tree_names(),
            requested_attributes=requested_attributes,
            skipped_attributes=skipped_attributes,
        )
        metadata_path = self.get_metadata_path()
        try:
            data_item.save_root_metadata(metadata_path)
        except NotImplementedError as error:
            self.warn_user(str(error))

    def end_of_simulation(self, item="all", **kwargs):
        self.store_runtime_metadata()


process_cls(ActorOutputBase)
process_cls(ActorOutputUsingDataItemContainer)
process_cls(ActorOutputImage)
process_cls(ActorOutputImageOfHistogram)
process_cls(ActorOutputSingleImage)
process_cls(ActorOutputSingleImageOfHistogram)
process_cls(ActorOutputSingleMeanImage)
process_cls(ActorOutputSingleImageWithVariance)
process_cls(ActorOutputQuotientImage)
process_cls(ActorOutputQuotientMeanImage)
process_cls(ActorOutputStatisticsActor)
process_cls(ActorOutputRoot)
