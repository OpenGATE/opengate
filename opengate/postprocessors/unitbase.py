import tables
from anytree import NodeMixin
from pathlib import Path

from .utility import (
    get_node_name,
    get_parent,
    get_node_path,
    get_create_function,
    set_node_name,
)
from ..base import GateObject
from ..exception import fatal
from ..utility import ensure_directory_exists

__run_group_prefix__ = "data_from_run"


def _setter_hook_yields_to(self, yields_to):
    try:
        unit_name = yields_to.name
    except AttributeError:
        unit_name = yields_to
    if self.processing_group is not None:
        self.processing_group._need_tree_update = True
    return unit_name


class ProcessingUnitBase(GateObject, NodeMixin):
    user_info_defaults = {
        "yields_to": (
            None,
            {
                "doc": "Processing unit that provides the input to this processing unit. ",
                "setter_hook": _setter_hook_yields_to,
            },
        ),
        "input_name": (
            None,
            {
                "doc": "Identifiers to specify the input data, usually node names. ",
            },
        ),
    }

    def __init__(self, *args, processing_group=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.processing_group = processing_group
        self.output_data_handles = {}
        self.input_data_handles = {}
        self.hdf5_group = None  # the hdf5 group where this unit stores its data

    @property
    def post_processor(self):
        if self.processing_group.is_post_processor:
            return self.processing_group
        else:
            return self.processing_group.post_processor

    @property
    def is_processing_unit(self):
        return True

    @property
    def can_be_initial_unit(self):
        """Generally, processing units cannot be the initial units in a processing tree.
        Those units which can be initial units, e.g. data fetcher, should override this property.
        """
        return False

    @property
    def output_file_handle(self):
        return self.post_processor.output_file_handle

    @property
    def input_units(self):
        if len(self.children) > 0:
            return self.children
        else:
            if self.processing_group is not None:
                try:
                    return self.processing_group.input_units
                except AttributeError:
                    return tuple()
            else:
                return tuple()

    def get_or_create_output_table(self, *args, **kwargs):
        return self._get_or_create_output_structure("tables", *args, **kwargs)

    def get_or_create_output_array(self, *args, **kwargs):
        return self._get_or_create_output_structure("array", *args, **kwargs)

    def get_or_create_output_carray(self, *args, **kwargs):
        return self._get_or_create_output_structure("carray", *args, **kwargs)

    def get_or_create_output_earray(self, *args, **kwargs):
        return self._get_or_create_output_structure("earray", *args, **kwargs)

    def get_or_create_output_group(self, *args, **kwargs):
        return self._get_or_create_output_structure("group", *args, **kwargs)

    def _get_or_create_output_structure(
        self, which, name, link_name=None, subgroup=None, external_file=False, **kwargs
    ):
        g = self.get_unit_output_group()
        if subgroup is not None:
            try:
                g = self.output_file_handle.get_node(g, subgroup)
            except tables.NoSuchNodeError:
                try:
                    g = self.output_file_handle.create_group(
                        g, subgroup, createparents=True
                    )
                except tables.NodeError as e:
                    fatal(
                        f"Could not create subgroup while creating table. The following exception occurred: "
                        f"{str(e)}"
                    )
        if external_file is False:
            try:
                return self.output_file_handle.get_node(g, name)
            except tables.NoSuchNodeError:
                return get_create_function(self.output_file_handle, which)(
                    g, name, **kwargs
                )
        else:
            if link_name is None:
                fatal(
                    f"You must provide a link_name when the option external_file=True. "
                )
            try:
                return self.output_file_handle.get_node(g, link_name)
            except tables.NoSuchNodeError:
                output_folder = (
                    self.post_processor.output_directory_external_files
                    / Path(get_node_path(g, strip_leading_slash=True))
                )
                ensure_directory_exists(output_folder)
                output_filename = f"{link_name}.h5"
                output_path = output_folder / output_filename
                print("output_path: ", output_path)
                f = self.post_processor.get_or_register_extra_file_handle(
                    tables.open_file(output_path, "w")
                )
                try:
                    s_external = f.get_node("/", name)
                except tables.NoSuchNodeError:
                    s_external = get_create_function(f, which)("/", name, **kwargs)
                # hdf5_path = get_node_path(s_external)
                link = self.post_processor.create_external_link(
                    g, link_name, s_external
                )  # this is a link object
                # g, name, f"{str(output_path)}:{hdf5_path}")  # this is a link object
                # node = link()  # l() returns the resolved link
                return link

    def register_output_data_handle(self, output_data_handle):
        """output_data_handle should be a mode in the hdf5_group belonging to this unit."""
        identifier = self.get_unique_identifier_within_unit(output_data_handle)
        # external links should need to be resolved before storage
        if hasattr(output_data_handle, "extfile"):
            _handle = output_data_handle(mode="a")
        else:
            _handle = output_data_handle
        if identifier not in self.output_data_handles:
            # set_node_name(_handle, identifier)  # don't change the target name!
            self.output_data_handles[identifier] = _handle
        else:
            fatal(f"An output data handle with this name already exists. ")
        return _handle

    def get_unique_identifier_within_unit(self, node):
        # construct a unique identifier.
        # If the output data handle is directly inside the output group of this unit,
        # the node name is guaranteed to be unique.
        # Otherwise, the subgroups needed to be considered as well (e.g. channels)
        items_to_combine = [node]
        counter = 0
        while get_parent(items_to_combine[-1]) is not self.hdf5_group:
            print(items_to_combine[-1])
            items_to_combine.append(get_parent(items_to_combine[-1]))
            if counter > 100:
                fatal(
                    f"Maximum recursion depth reached. "
                    f"Something went wrong while trying to find a unique identifier "
                    f"for node {get_node_name(items_to_combine[0])}"
                )
            counter += 1
        return "_".join([get_node_name(n) for n in items_to_combine])

    def get_title_for_hdf5_node(self):
        return f"{type(self).__name__}_{self.name}"

    def update_tree_node(self):
        """Internal method which retrieves the volume object
        from the volume manager based on the mother's name stored as user info 'mother'
        """
        if self.processing_group is not None:
            if self.yields_to is not None:
                try:
                    self.parent = self.processing_group.get_processing_unit(
                        self.yields_to
                    )
                except KeyError:
                    fatal(
                        f"Error while trying to update the hierarchy relationship of processing unit {self.name}. "
                        f"Input unit {self.yields_to} not found in processing group {self.processing_group.name}."
                    )
            else:
                self.parent = None
        else:
            fatal(
                f"Cannot update hierarchy of processing unit {self.name} "
                f"because it is not attached to any processing group. "
            )

    def _request_processing_unit_tree_update(self):
        if self.processing_group is not None:
            self.processing_group.update_processing_tree()
        else:
            fatal(
                f"Cannot update hierarchy of processing unit {self.name} "
                f"because it is not attached to any processing group. "
            )

    def initialize_hdf5_group_in_output_file(self):
        if self.hdf5_group is None:
            if self.processing_group.hdf5_group is None:
                self.processing_group.initialize_hdf5_group_in_output_file()
            self.hdf5_group = self.output_file_handle.create_group(
                self.processing_group.hdf5_group, self.name
            )

    def get_unit_output_group(self):
        return self.hdf5_group

    def store_user_attributes(self):
        attrs = self.get_unit_output_group()._v_attrs
        for k, v in self.to_dictionary().items():
            setattr(attrs, k, v)

    def close(self):
        super().close()
        for k in self.input_data_handles.keys():
            self.input_data_handles[k] = None
        for child in self.children:
            child.close()

    def update_output(self):
        # do not override this method in derived classes
        for child in self.children:
            child.update_output()
        self.do_your_job()
        self.store_user_attributes()
        print(f"updated {self.name}")

    def do_your_job(self):
        """Implement this in the concrete class."""
        pass
