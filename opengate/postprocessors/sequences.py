from .utility import create_hard_links_to_nodes_in_group
from ..exception import fatal
from .base import ProcessingGroupBase
from .unitbase import ProcessingUnitBase


class ProcessingSequence(ProcessingGroupBase, ProcessingUnitBase):
    """A special kind of processing group that has only one branch,
    i.e. a single root and each node has a single child only.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update_processing_tree(self):
        super().update_processing_tree()
        tree_roots = self.tree_roots
        if len(tree_roots) > 1:
            fatal(f"Processing sequence {self.name} has more than one tree root. ")
        if len(list(tree_roots)[0].leaves) > 1:
            fatal(f"Processing sequence {self.name} has more than one leaf. ")

    def get_unit_output_group(self):
        return self.get_output_groups()[0]

    def do_your_job(self):
        self.tree_roots[0].update_output()
        for k, v in self.tree_roots[0].output_data_handles.items():
            self.output_data_handles[k] = v
        create_hard_links_to_nodes_in_group(
            self.hdf5_group, self.get_unit_output_group()
        )
