"""Internal ROOT I/O infrastructure used by actor outputs and jobs merge.

This module is intentionally separate from ``opengate.contrib.root_helpers``.
The contrib helpers are user-facing utilities for ad hoc ROOT
post-processing, whereas the classes and helpers here are part of GATE's
internal actor-output persistence and merge machinery.
"""

from pathlib import Path

import awkward as ak
import numpy as np
import uproot

from .exception import GateMergeError


def _normalize_writable_branch_payload(branch_payload):
    """Convert one streamed ROOT chunk into uproot-writable arrays."""

    def _normalize_one_branch(value):
        if isinstance(value, np.ndarray):
            if value.dtype == object:
                value = value.tolist()
            if value.ndim == 0:
                return np.asarray([value.item()])
            return value
        try:
            len(value)
        except TypeError:
            value = [value]
        return ak.Array(value)

    return {k: _normalize_one_branch(v) for k, v in branch_payload.items()}


class RootMergeFileWriter:
    """Incremental ROOT writer used by split-job merge.

    The writer owns one physical ROOT file and keeps writable tree handles open
    so multiple actor outputs can stream chunks into distinct trees of the same
    file without repeatedly recreating it.
    """

    def __init__(self, output_path):
        self.output_path = Path(output_path)
        self._file = None
        self._trees = {}

    def open(self):
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = uproot.recreate(self.output_path)

    def create_tree(self, tree_name, branch_types):
        if self._file is None:
            raise RuntimeError(
                "RootMergeFileWriter.create_tree() called before open()."
            )
        if tree_name in self._trees:
            return self._trees[tree_name]
        tree = self._file.mktree(tree_name, branch_types)
        self._trees[tree_name] = tree
        return tree

    def append_chunk(self, tree_name, branch_payload):
        if tree_name not in self._trees:
            raise RuntimeError(
                f"RootMergeFileWriter.append_chunk() received unknown tree "
                f"'{tree_name}'. Call create_tree() first."
            )
        self._trees[tree_name].extend(
            _normalize_writable_branch_payload(branch_payload)
        )

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None
            self._trees = {}


class RootMergeCoordinator:
    """Grouped ROOT merge executor for split-job merge finalization.

    The coordinator acts as a merge-time proxy for ROOT-backed actor outputs
    that cannot be finalized independently one-by-one. Several actor outputs
    may target distinct trees in the same physical ROOT file, so letting each
    actor output finalize itself in isolation would repeatedly recreate or
    reopen the same file and would obscure the shared-file merge contract.

    Instead, standard non-ROOT outputs are handled by a separate merge
    coordinator, while ROOT-backed outputs register with this coordinator. The
    coordinator then groups them by target file, collects their ROOT merge
    metadata during execute_merge(), and performs one shared streaming merge
    per physical ROOT file during finalize_merge().
    """

    def __init__(self):
        self._root_output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}

    def configure_from_context(self, root_context, target_simulation):
        """Build grouped ROOT merge work from the planned merge context.

        The coordinator is intentionally configured during planning rather than
        rediscovering ROOT outputs later during simulation finalization.
        """
        self._root_output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}
        for root_output_plan in root_context.iter_output_plans():
            actor_name = root_output_plan["actor_name"]
            output_name = root_output_plan["output_name"]
            actor = target_simulation.get_actor(actor_name)
            actor_output = actor.user_output.get(output_name)
            if actor_output is None:
                raise GateMergeError(
                    f"Cannot configure ROOT merge for unknown output '{output_name}' "
                    f"on actor '{actor_name}'."
                )
            if actor_output.is_root_output() is not True:
                raise GateMergeError(
                    f"Planned ROOT merge output '{output_name}' on actor "
                    f"'{actor_name}' is not a ROOT output at execution time."
                )
            if actor_output.get_write_to_disk(item=0) is not True:
                continue
            output_path = actor_output.get_output_path(which="merged")
            if output_path is None:
                continue
            contributions = root_context.get_contributions_for_output(
                actor_name, output_name
            )
            contributions_by_job = {}
            for contribution in contributions:
                if contribution.get("mergeable") is not True:
                    continue
                job_index = contribution["job_index"]
                contributions_by_job.setdefault(job_index, []).append(contribution)
                self._source_infos[job_index] = root_context.get_source_info(job_index)
            self._root_output_groups.setdefault(Path(output_path).resolve(), []).append(
                {
                    "target_output": actor_output,
                    "contributions_by_job": contributions_by_job,
                }
            )

    def _get_source_simulation(self, job_index):
        if job_index not in self._source_simulations_by_job_index:
            from .managers import create_sim_from_json

            source_info = self._source_infos[job_index]
            child_simulation = create_sim_from_json(source_info["simulation_path"])
            child_simulation.root_dir = Path(source_info["folder"])
            child_simulation.output_dir = Path(source_info["folder"]) / "output"
            self._source_simulations_by_job_index[job_index] = child_simulation
        return self._source_simulations_by_job_index[job_index]

    def execute_merge(self):
        from .jobs import _CoordinatorOutputMergeContext

        for grouped_outputs in self._root_output_groups.values():
            for grouped_output in grouped_outputs:
                target_output = grouped_output["target_output"]
                actor_name = target_output.belongs_to_actor.name
                output_name = target_output.name
                for job_index, contributions in grouped_output[
                    "contributions_by_job"
                ].items():
                    source_simulation = self._get_source_simulation(job_index)
                    source_actor = source_simulation.get_actor(actor_name)
                    source_output = source_actor.user_output[output_name]
                    target_output.execute_merge(
                        source_output,
                        context=_CoordinatorOutputMergeContext(contributions),
                    )

    def finalize_merge(self):
        for output_path, grouped_outputs in self._root_output_groups.items():
            writer = RootMergeFileWriter(output_path)
            writer.open()
            try:
                event_id_states_by_tree = {}
                active_root_outputs = []

                for grouped_output in grouped_outputs:
                    actor_output = grouped_output["target_output"]
                    data_container = actor_output.get_data_container("merged")
                    if data_container is None:
                        continue
                    data_item = data_container.get_data_item_object(0)
                    if (
                        data_item is None
                        or not data_item.has_root_meta_data()
                        or len(data_item.root_meta_data.get("merge_sources", [])) == 0
                    ):
                        continue
                    tree_descriptor = data_item.get_single_tree_descriptor()
                    writer.create_tree(
                        tree_descriptor["tree_name"], tree_descriptor["branches"]
                    )
                    active_root_outputs.append(
                        (actor_output, data_item, tree_descriptor)
                    )

                for actor_output, data_item, tree_descriptor in active_root_outputs:
                    event_id_state = event_id_states_by_tree.setdefault(
                        tree_descriptor["tree_name"], {"next_event_id": 0}
                    )
                    data_item.stream_write_merged_root(
                        output_path,
                        metadata_path=actor_output.get_metadata_path(),
                        writer=writer,
                        event_id_state=event_id_state,
                    )
            finally:
                writer.close()
