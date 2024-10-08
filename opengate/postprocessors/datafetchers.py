import tables
from pathlib import Path

from ..exception import fatal
from .utility import get_nodes_in_group, get_node_name
from .unitbase import ProcessingUnitBase


def _setter_hook_input_path(self, p):
    if self.user_info["actor_output"] is None:
        return Path(p)
    else:
        fatal(
            f"Cannot set 'input_path' and 'actor_output'. Unset one before setting the other. "
        )


def _setter_hook_input_actor(self, input_actor):
    if self.user_info["input_actor"] is None:
        try:
            n = input_actor.name
        except AttributeError:
            n = input_actor
        return n
    else:
        fatal(
            f"Cannot set 'input_path' and 'input_actor'. Unset one before setting the other. "
        )


class DataFetcherBase(ProcessingUnitBase):
    """This is a base class for data fetchers."""

    user_info_defaults = {
        "input_path": (
            None,
            {
                "doc": "Path to the input file. ",
                "setter_hook": _setter_hook_input_path,
            },
        ),
        "actor_output": (
            None,
            {
                "doc": "Actor that provides data. ",
                "setter_hook": _setter_hook_input_actor,
            },
        ),
        "which_output": (
            "merged_data",
            {
                "doc": "Which kind of output should be taken from the actor? "
                "Allowed values: 'merged_data' or a valid run index.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._input_path = None  # internal variable to store input path

    @property
    def can_be_initial_unit(self):
        return True

    def _get_input_path(self):
        if self.input_path is not None:
            return Path(self.input_path).absolute()
        elif self.actor_output is not None:
            return self.actor_output.get_output_path(self.which_output)
        else:
            return None

    def close(self):
        super().close()
        self._input_path = None


class DataFetcherWithFileHandle(DataFetcherBase):

    def _open_input_file_handle(self):
        input_path = self._get_input_path()
        if self._input_path is None:
            if not self.post_processor.has_extra_file_handle(input_path):
                self.post_processor.get_or_register_extra_file_handle(
                    self.open_file(input_path)
                )
            self._input_path = input_path

    def open_file(self, path):
        """Needs concrete implementation in derived class."""
        raise NotImplementedError

    @property
    def input_file_handle(self):
        return self.post_processor.get_extra_file_handle(self._input_path)


def _setter_hook_path_in_hdf5_file(self, p):
    if not p.startswith("/"):
        p = "/" + p
    return p


class DataFetcherHdf5(DataFetcherWithFileHandle):
    user_info_defaults = {
        # "hdf5_node_name": (
        #     None,
        #     {
        #         "doc": "Name of the attribute to be blurred.",
        #     },
        # ),
        "input_hdf5_group": (
            "/",
            {
                "doc": "Name of the attribute to be blurred.",
                "setter_hook": _setter_hook_path_in_hdf5_file,
            },
        ),
    }

    def open_file(self, path):
        return tables.open_file(path, mode="r", title=self.get_title_for_hdf5_node())

    def do_your_job(self):
        self._open_input_file_handle()
        input_group = self.input_file_handle.get_node(
            "/", name=self.input_hdf5_group.lstrip("/")
        )
        nodes = get_nodes_in_group(input_group, node_name=self.input_name)
        print("Nodes in DataFetcherHdf5.do_your_job()")
        for n in nodes:
            print(n)
            self.register_output_data_handle(
                self.post_processor.create_external_link(
                    self.get_unit_output_group(), get_node_name(n), target=n
                )
            )
