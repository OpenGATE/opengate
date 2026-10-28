from pathlib import Path

from .exception import GateMergeError
from .rootio import RootMergeFileWriter


class _CoordinatorOutputMergeContext:
    """Minimal output-scoped execution context consumed by ActorOutput classes."""

    def __init__(self, contributions, load_mode="rehydrated"):
        self._contributions = list(contributions)
        self._load_mode = load_mode

    def get_contributions(self):
        return self._contributions

    def get_load_mode(self, default="rehydrated"):
        return self._load_mode if self._load_mode is not None else default


class StandardMergeCoordinator:
    """Execute and finalize merge for standard non-ROOT actor outputs."""

    def __init__(self):
        self._output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}

    def configure_from_context(self, standard_context, target_simulation):
        self._output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}

        for output_plan in standard_context.iter_output_plans():
            actor_name = output_plan["actor_name"]
            output_name = output_plan["output_name"]
            actor = target_simulation.get_actor(actor_name)
            target_output = actor.user_output.get(output_name)
            if target_output is None:
                raise GateMergeError(
                    f"Cannot configure standard merge for unknown output '{output_name}' "
                    f"on actor '{actor_name}'."
                )
            if target_output.is_container_output() is not True:
                actor.warn_user(
                    f"Skipping unmergeable actor output '{output_name}' "
                    f"from actor '{actor_name}' during merge coordination. "
                    "Only container-based actor outputs are currently handled "
                    "by the jobs-merge framework."
                )
                continue
            contributions = standard_context.get_contributions_for_output(
                actor_name, output_name
            )
            contributions_by_job = {}
            for contribution in contributions:
                if contribution.get("mergeable") is not True:
                    continue
                job_index = contribution["job_index"]
                contributions_by_job.setdefault(job_index, []).append(contribution)
                self._source_infos[job_index] = standard_context.get_source_info(
                    job_index
                )
            self._output_groups[(actor_name, output_name)] = {
                "target_output": target_output,
                "contributions_by_job": contributions_by_job,
            }

    def _get_source_simulation(self, job_index):
        if job_index not in self._source_simulations_by_job_index:
            from .managers import create_sim_from_json

            source_info = self._source_infos[job_index]
            child_simulation = create_sim_from_json(source_info["simulation_path"])
            child_simulation.simulation_dir = Path(source_info["folder"])
            child_simulation.output_dir = Path(source_info["folder"]) / "output"
            self._source_simulations_by_job_index[job_index] = child_simulation
        return self._source_simulations_by_job_index[job_index]

    def execute_merge(self):
        for (actor_name, output_name), group in self._output_groups.items():
            target_output = group["target_output"]
            for job_index, contributions in group["contributions_by_job"].items():
                source_simulation = self._get_source_simulation(job_index)
                source_actor = source_simulation.get_actor(actor_name)
                source_output = source_actor.user_output[output_name]
                try:
                    target_output.execute_merge(
                        source_output,
                        context=_CoordinatorOutputMergeContext(contributions),
                    )
                except Exception as error:
                    if isinstance(error, GateMergeError):
                        raise GateMergeError(
                            f"Failed to execute standard merge for actor output "
                            f"'{output_name}' of actor '{actor_name}' from job_index "
                            f"{job_index}."
                        ) from error
                    raise GateMergeError(
                        f"Unexpected failure while executing standard merge for "
                        f"actor output '{output_name}' of actor '{actor_name}' "
                        f"from job_index {job_index}."
                    ) from error

    def finalize_merge(self):
        for (actor_name, output_name), group in self._output_groups.items():
            try:
                group["target_output"].finalize_merge()
            except Exception as error:
                if isinstance(error, GateMergeError):
                    raise GateMergeError(
                        f"Failed to finalize standard merge for actor output "
                        f"'{output_name}' of actor '{actor_name}'."
                    ) from error
                raise GateMergeError(
                    f"Unexpected failure while finalizing standard merge for actor "
                    f"output '{output_name}' of actor '{actor_name}'."
                ) from error


class RootMergeCoordinator:
    """Grouped ROOT merge executor for split-job merge finalization."""

    def __init__(self):
        self._root_output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}

    def configure_from_context(self, root_context, target_simulation):
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
            child_simulation.simulation_dir = Path(source_info["folder"])
            child_simulation.output_dir = Path(source_info["folder"]) / "output"
            self._source_simulations_by_job_index[job_index] = child_simulation
        return self._source_simulations_by_job_index[job_index]

    def execute_merge(self):
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
