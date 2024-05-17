from anytree import LoopError
from pathlib import Path
import tables
from collections import OrderedDict
import inspect

import opengate.postprocessors

# from .datafetchers import DataFetcherHdf5
# from .image import ProjectionListMode
# from .listmode import ListModeSingleAttribute, GaussianBlurringSingleAttribute, \
#     OffsetSingleAttribute
# from .sequences import ProcessingSequence
from ..base import GateObject
from ..exception import fatal
from ..utility import ensure_directory_exists

__run_group_prefix__ = "data_from_run"


class ProcessingGroupBase(GateObject):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processing_units = OrderedDict()
        self._need_tree_update = True  # flag to store state of processing unit tree

    def close(self):
        for r in self.tree_roots:
            r.close()
        self._need_tree_update = True

    def to_dictionary(self):
        d = super().to_dictionary()
        d["processing_units"] = dict(
            [(k, v.to_dictionary()) for k, v in self.processing_units.items()]
        )
        return d

    @property
    def last_added_processing_unit(self):
        return self.processing_units[next(reversed(self.processing_units))]

    def add_processing_unit(self, processing_unit, **kwargs):
        try:
            is_unit = processing_unit.is_processing_unit
        except AttributeError:
            is_unit = False
        if is_unit:
            _processing_unit = processing_unit
        else:
            try:
                processing_unit_class = (
                    opengate.postprocessors.available_processing_units[processing_unit]
                )
            except KeyError:
                fatal(
                    f"Invalid input for processing_unit. "
                    f"Should be an instance of a processing unit class or a known processing unit name. "
                    f"Available classes are: {list(opengate.postprocessors.available_processing_units.keys())}"
                )
            _processing_unit = processing_unit_class(**kwargs)
        if _processing_unit.name not in self.processing_units:
            _processing_unit.processing_group = self
            _processing_unit.simulation = self.simulation
            # automatically set hierarchy, (can be changed manually by user):
            if len(self.processing_units) > 0:
                self.last_added_processing_unit.yields_to = _processing_unit
            if hasattr(_processing_unit, "processing_units"):
                for u in _processing_unit.processing_units.values():
                    u.simulation = self.simulation
            self.processing_units[_processing_unit.name] = _processing_unit
        else:
            fatal(
                f"ProcessingGroup {self.name} already contains a post-processing unit named {_processing_unit.name}. "
            )
        self._need_tree_update = True
        # if the instance has only been created here, return it.
        if _processing_unit is not processing_unit:
            return _processing_unit

    def get_processing_unit(self, name):
        try:
            return self.processing_units[name]
        except KeyError:
            fatal(
                f"No unit with the name {name} found. Known units are: {list(self.processing_units.keys())}"
            )

    @property
    def all_processing_units(self):
        all_units = set()
        for u in self.processing_units.values():
            all_units.add(u)
            try:
                all_units.update(u.all_processing_units)
            except AttributeError:
                pass
        return all_units

    @property
    def is_post_processor(self):
        if isinstance(self, PostProcessor):
            return True
        else:
            return False

    @property
    def tree_roots(self):
        self.update_processing_tree_if_needed()
        tree_roots = set()
        for v in self.processing_units.values():
            tree_roots.add(v.root)
        return tuple(tree_roots)

    def get_output_groups(self):
        return [tr.hdf5_group for tr in self.tree_roots]

    def update_processing_tree(self):
        for v in self.processing_units.values():
            try:
                v.update_tree_node()
            except LoopError:
                fatal(
                    f"There seems to be a loop in the processing unit tree involving unit {v.name}."
                )
            try:
                v.update_processing_tree()
            except AttributeError:
                pass
        self._need_tree_update = False

    def update_processing_tree_if_needed(self):
        if self._need_tree_update:
            self.update_processing_tree()

    @property
    def processing_groups(self):
        return [
            u
            for u in self.processing_units.values()
            if isinstance(u, ProcessingGroupBase)
        ]


class PostProcessor(ProcessingGroupBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_file_handle = None
        self.extra_file_handles = {}

    def initialize(self):
        self.update_processing_tree()
        for n in self.all_initial_units:
            # make sure all input units are data fetcher
            if n.can_be_initial_unit is False:
                fatal(f"Input node {n.name} is not a data fetcher. ")

        self.initialize_output_file()
        self.initialize_hdf5_groups()

    def initialize_output_file(self):
        if self.output_file_handle is None:
            self.output_file_handle = tables.open_file(
                self.simulation.get_output_path(f"output_{self.name}.h5"),
                mode="w",
                title=f"Output post-processor {self.name}",
            )
        ensure_directory_exists(self.output_directory_external_files)

    @property
    def output_directory_external_files(self):
        output_directory = self.output_directory
        if output_directory is None:
            return None
        else:
            return output_directory / (
                Path(self.output_file_handle.filename).stem.rstrip("_")
                + "_external_files"
            )

    @property
    def output_directory(self):
        if self.output_file_handle is not None:
            return Path(self.output_file_handle.filename).parent
        else:
            return None

    def get_extra_file_handle(self, identifier):
        try:
            return self.extra_file_handles[str(identifier)]
        except KeyError:
            raise KeyError(
                f"Cannot find an input file handle for identifier '{identifier}'."
            )

    def get_or_register_extra_file_handle(self, file_handle):
        """Register a handle if it is not known yet."""
        identifier = str(file_handle.filename)
        print(f"register_extra_file_handle {identifier}")
        try:
            return self.get_extra_file_handle(identifier)
        except KeyError:
            self.extra_file_handles[identifier] = file_handle
            return file_handle

    def has_extra_file_handle(self, identifier):
        try:
            self.get_extra_file_handle(identifier)
            return True
        except KeyError:
            return False

    # def get_external_link_file_handle(self, identifier):
    #     try:
    #         return self.external_link_file_handles[identifier]
    #     except KeyError:
    #         raise KeyError(f"Cannot find an external link file handle for identifier '{identifier}'.")
    #
    # def register_external_link_file_handle(self, file_handle):
    #     """Register a handle if it is not known yet. """
    #     identifier = file_handle.filename
    #     if self.get_extra_file_handle(identifier) is None:
    #         self.external_link_file_handles[identifier] = file_handle

    def create_external_link(self, where, name, target, createparents=False):
        """Create an external link.

        Create an external link to a *target* node with the given *name*
        in *where* location.  *target* can be a node object in another
        file or a path string in the form 'file:/path/to/node'.  If
        *createparents* is true, the intermediate groups required for
        reaching *where* are created (the default is not doing so).

        The returned node is an :class:`ExternalLink` instance.

        """

        if not isinstance(target, str):
            if hasattr(target, "_v_pathname"):  # quacks like a Node
                target = target._v_file.filename + ":" + target._v_pathname
            else:
                raise ValueError("`target` has to be a string or a node object")
        elif target.find(":/") == -1:
            raise ValueError("`target` must expressed as 'file:/path/to/node'")
        parentnode = self.output_file_handle._get_or_create_path(where, createparents)
        elink = ManagedExternalLink(self, parentnode, name, target)
        # Refresh children names in link's parent node
        parentnode._g_add_children_names()
        return elink

    def release_file_handles(self):
        for k, v in self.extra_file_handles.items():
            v.close()
        self.extra_file_handles = {}
        self.output_file_handle.close()
        self.output_file_handle = None

    def close(self):
        super().close()  # this closes all data handles
        self.release_file_handles()

    def run(self):
        try:
            self.initialize()
            for tr in self.tree_roots:
                tr.update_output()
            self.output_file_handle.flush()
        finally:
            self.close()

    @property
    def hdf5_group(self):
        if self.output_file_handle is not None:
            return self.output_file_handle.get_node("/")
        else:
            return None

    def initialize_hdf5_groups(self):
        for u in self.all_processing_units:
            u.initialize_hdf5_group_in_output_file()

    @property
    def all_initial_units(self):
        """Get all"""
        initial_units = []
        for tr in self.tree_roots:
            initial_units.extend(tr.leaves)
        return initial_units


class ManagedExternalLink(tables.linkextension.ExternalLink, tables.link.Link):
    """Variant of the ExternalLink class from PyTables."""

    # Class identifier.
    _c_classid = "MANAGEDEXTERNALLINK"

    def __init__(self, post_processor, parentnode, name, target=None, _log=False):
        # self.extfile = None  # PyTables' ExternalLink class defines this attribute.
        self.post_processor = post_processor
        """The external file handler, if the link has been dereferenced.
        In case the link has not been dereferenced yet, its value is
        None."""
        super().__init__(parentnode, name, target, _log)

    @property
    def extfile(self):
        filename, target = self._get_filename_node()
        absolute_path = str(Path(filename).absolute())
        try:
            return self.post_processor.get_extra_file_handle(absolute_path)
        except KeyError:
            return None

    @extfile.setter
    def extfile(self, file_handle):
        self.post_processor.get_or_register_extra_file_handle(file_handle)

    def _get_filename_node(self):
        """Return the external filename and nodepath from `self.target`."""

        # This is needed for avoiding the 'C:\\file.h5' filepath notation
        filename, target = self.target.split(":/")
        return filename, "/" + target

    def __call__(self, **kwargs):
        """Dereference self.target and return the object.

        You can pass all the arguments supported by the :func:`open_file`
        function (except filename, of course) so as to open the referenced
        external file.
        """

        filename, target = self._get_filename_node()

        if not Path(filename).is_absolute():
            # Resolve the external link with respect to the this
            # file's directory.  See #306.
            filename = str(Path(self._v_file.filename).with_name(filename))

        if self.extfile is None or not self.extfile.isopen:
            self.extfile = tables.open_file(filename, **kwargs)
        else:
            # XXX: implement better consistency checks
            assert self.extfile.filename == filename
            # assert self.extfile.mode == kwargs.get('mode', 'r')

        return self.extfile._get_node(target)

    def umount(self):
        """Safely unmount self.extfile, if opened."""

        extfile = self.extfile
        # Close external file, if open
        if extfile is not None and extfile.isopen:
            extfile.close()
            self.extfile = None

    # def _f_close(self):
    #     """Especific close for external links."""
    #
    #     self.umount()
    #     super()._f_close()

    def __str__(self):
        """Return a short string representation of the link."""

        return f"{self._v_pathname} ({self.__class__.__name__}) -> " f"{self.target}"


# available_processing_units = {
#     'ProcessingSequence': ProcessingSequence,
#     'DataFetcherHdf5': DataFetcherHdf5,
#     'ProcessingUnitListModeSingleAttribute': ListModeSingleAttribute,
#     'GaussianBlurringSingleAttribute': GaussianBlurringSingleAttribute,
#     'OffsetSingleAttribute': OffsetSingleAttribute,
#     'ProjectionFromListMode': ProjectionListMode
# }
