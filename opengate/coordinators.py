import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path

from .exception import GateMergeError
from .profiling import Profilable, profile_method
from .rootio import RootMergeFileWriter, normalize_root_output_compression


def _diagnostic_process_memory_snapshot():
    """Return native process-memory counters for the ROOT merge study.

    DIAGNOSTIC ONLY: this deliberately imports the optional benchmark dependency
    lazily and must not be used by normal merge execution.
    """

    try:
        import psutil
    except ImportError as error:
        raise RuntimeError(
            "Diagnostic ROOT chunk profiling requires psutil."
        ) from error

    process = psutil.Process()
    snapshot = {"rss_bytes": process.memory_info().rss}
    try:
        snapshot["uss_bytes"] = process.memory_full_info().uss
    except (AttributeError, psutil.Error, OSError):
        snapshot["uss_bytes"] = None
    return snapshot


def _diagnostic_prefixed_process_memory_snapshot(prefix):
    return {
        f"{prefix}_{name}": value
        for name, value in _diagnostic_process_memory_snapshot().items()
    }


def _output_contribution_metadata(
    target_output, job_index, *, coordinator, phase, **metadata
):
    """Describe one actor-output contribution using a coordinator-neutral schema."""

    return {
        "actor_name": target_output.belongs_to_actor.name,
        "output_name": target_output.name,
        "output_type": type(target_output).__name__,
        "job_index": job_index,
        "coordinator": coordinator,
        "phase": phase,
        **metadata,
    }


def _progress_bar(coordinator, total, label):
    """Progress of the merge of one actor output (see progress_bar_factory,
    set by JobsMergeManager with the option progress), else None."""
    factory = getattr(coordinator, "progress_bar_factory", None)
    return None if factory is None else factory(total, label)


class _CoordinatorOutputMergeContext:
    """Minimal output-scoped execution context consumed by ActorOutput classes."""

    def __init__(self, contributions, load_mode="rehydrated", source_info=None):
        self._contributions = list(contributions)
        self._load_mode = load_mode
        self._source_info = dict(source_info) if source_info is not None else {}

    def get_contributions(self):
        return self._contributions

    def get_source_info(self):
        return self._source_info

    def get_local_to_original_run_map(self):
        """Original run index of each local run of the source job (None if unknown)."""
        run_map = self._source_info.get("local_to_original_run_map")
        return None if run_map is None else list(run_map)

    def get_load_mode(self, default="rehydrated"):
        return self._load_mode if self._load_mode is not None else default


class StandardMergeCoordinator(Profilable):
    """Execute and finalize merge for standard non-ROOT actor outputs."""

    def __init__(self):
        self.initialize_profiler(name="StandardMergeCoordinator")
        self._output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}
        self._source_simulation_loader = None

    @profile_method("configure")
    def configure_from_context(
        self, standard_context, target_simulation, source_simulation_loader=None
    ):
        self._output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}
        self._source_simulation_loader = source_simulation_loader

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
        if self._source_simulation_loader is not None:
            # loaded once, shared with the planning and the other coordinators
            return self._source_simulation_loader(self._source_infos[job_index])
        if job_index not in self._source_simulations_by_job_index:
            from .managers import create_sim_from_json

            source_info = self._source_infos[job_index]
            child_simulation = create_sim_from_json(source_info["simulation_path"])
            child_simulation.simulation_dir = Path(source_info["folder"])
            child_simulation.output_dir = Path(source_info["folder"]) / "output"
            self._source_simulations_by_job_index[job_index] = child_simulation
        return self._source_simulations_by_job_index[job_index]

    @profile_method("execute")
    def execute_merge(self):
        # progress: one line per actor (all its outputs)
        totals = {}
        n_outputs = {}
        for (actor_name, _), group in self._output_groups.items():
            totals[actor_name] = totals.get(actor_name, 0) + len(
                group["contributions_by_job"]
            )
            n_outputs[actor_name] = n_outputs.get(actor_name, 0) + 1
        bar = None
        bar_actor = None
        done = 0
        for (actor_name, output_name), group in self._output_groups.items():
            if actor_name != bar_actor:
                if bar is not None:
                    bar.update(done)
                    bar.close()
                label = actor_name
                if n_outputs[actor_name] > 1:
                    label += f" ({n_outputs[actor_name]} outputs x jobs)"
                bar = _progress_bar(self, totals[actor_name], label)
                bar_actor = actor_name
                done = 0
            target_output = group["target_output"]
            for job_index, contributions in group["contributions_by_job"].items():
                if bar is not None:
                    bar.update(done)
                done += 1
                source_simulation = self._get_source_simulation(job_index)
                source_actor = source_simulation.get_actor(actor_name)
                source_output = source_actor.user_output[output_name]
                source_paths = sorted(
                    {
                        contribution["output_path"]
                        for contribution in contributions
                        if contribution.get("output_path") is not None
                    }
                )
                try:
                    if self.profiler.enabled:
                        with self.profiler.measure(
                            "output_contribution",
                            metadata=_output_contribution_metadata(
                                target_output,
                                job_index,
                                coordinator="standard",
                                phase="execute",
                                source_paths=source_paths,
                            ),
                        ):
                            target_output.execute_merge(
                                source_output,
                                context=_CoordinatorOutputMergeContext(
                                    contributions,
                                    source_info=self._source_infos.get(job_index),
                                ),
                            )
                    else:
                        target_output.execute_merge(
                            source_output,
                            context=_CoordinatorOutputMergeContext(
                                contributions,
                                source_info=self._source_infos.get(job_index),
                            ),
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
        if bar is not None:
            bar.update(done)
            bar.close()

    @profile_method("finalize")
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


class RootMergeCoordinator(Profilable):
    """Grouped ROOT merge executor for split-job merge finalization.

    ``chunk_size`` controls the amount streamed through memory at once.
    ``decompression_workers`` enables Uproot's thread-based basket
    decompression; writing and identifier remapping remain ordered.
    """

    def __init__(
        self,
        *,
        compression="zlib",
        chunk_size="64 MB",
        decompression_workers=1,
        diagnostic_chunk_profiling=False,
        diagnostic_release_chunk_references=False,
    ):
        self.initialize_profiler(name="RootMergeCoordinator")
        self.compression = normalize_root_output_compression(compression)
        self.chunk_size = chunk_size
        self.decompression_workers = int(decompression_workers)
        if self.decompression_workers < 1:
            raise ValueError("decompression_workers must be at least one.")
        # DIAGNOSTIC ONLY: these switches support the multi-job memory study and
        # intentionally stay disabled in regular ROOT merge execution.
        self.diagnostic_chunk_profiling = bool(diagnostic_chunk_profiling)
        self.diagnostic_release_chunk_references = bool(
            diagnostic_release_chunk_references
        )
        if self.diagnostic_release_chunk_references:
            self.diagnostic_chunk_profiling = True
        self._root_output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}
        self._source_simulation_loader = None

    @profile_method("configure")
    def configure_from_context(
        self, root_context, target_simulation, source_simulation_loader=None
    ):
        self._root_output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}
        self._source_simulation_loader = source_simulation_loader
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
        if self._source_simulation_loader is not None:
            # loaded once, shared with the planning and the other coordinators
            return self._source_simulation_loader(self._source_infos[job_index])
        if job_index not in self._source_simulations_by_job_index:
            from .managers import create_sim_from_json

            source_info = self._source_infos[job_index]
            child_simulation = create_sim_from_json(source_info["simulation_path"])
            child_simulation.simulation_dir = Path(source_info["folder"])
            child_simulation.output_dir = Path(source_info["folder"]) / "output"
            self._source_simulations_by_job_index[job_index] = child_simulation
        return self._source_simulations_by_job_index[job_index]

    @profile_method("execute")
    def execute_merge(self):
        for grouped_outputs in self._root_output_groups.values():
            for grouped_output in grouped_outputs:
                target_output = grouped_output["target_output"]
                actor_name = target_output.belongs_to_actor.name
                output_name = target_output.name
                n = len(grouped_output["contributions_by_job"])
                bar = _progress_bar(self, n, f"{actor_name} {output_name}")
                for i, (job_index, contributions) in enumerate(
                    grouped_output["contributions_by_job"].items()
                ):
                    if bar is not None:
                        bar.update(i)
                    source_simulation = self._get_source_simulation(job_index)
                    source_actor = source_simulation.get_actor(actor_name)
                    source_output = source_actor.user_output[output_name]
                    target_output.execute_merge(
                        source_output,
                        context=_CoordinatorOutputMergeContext(
                            contributions,
                            source_info=self._source_infos.get(job_index),
                        ),
                    )
                if bar is not None:
                    bar.update(n)
                    bar.close()

    @profile_method("finalize")
    def finalize_merge(self):
        timing = defaultdict(float) if self.profiler.enabled else None
        executor_context = (
            ThreadPoolExecutor(max_workers=self.decompression_workers)
            if self.decompression_workers > 1
            else nullcontext(None)
        )
        with executor_context as decompression_executor:
            self._finalize_merge_outputs(decompression_executor, timing)
        if timing is not None:
            for name, value in timing.items():
                self.profiler.set_value(f"streaming.{name}", value)
            self.profiler.set_value("streaming.compression", self.compression)
            self.profiler.set_value("streaming.chunk_size", self.chunk_size)
            self.profiler.set_value(
                "streaming.decompression_workers", self.decompression_workers
            )

    def _finalize_merge_outputs(self, decompression_executor, timing):
        for output_path, grouped_outputs in self._root_output_groups.items():
            writer = RootMergeFileWriter(
                output_path,
                compression=self.compression,
            )
            started_at = time.perf_counter() if timing is not None else None
            writer.open()
            if timing is not None:
                timing["open_s"] += time.perf_counter() - started_at
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
                    started_at = (
                        time.perf_counter() if timing is not None else None
                    )
                    writer.create_tree(
                        tree_descriptor["tree_name"], tree_descriptor["branches"]
                    )
                    if timing is not None:
                        timing["create_tree_s"] += time.perf_counter() - started_at
                    active_root_outputs.append(
                        (actor_output, data_item, tree_descriptor)
                    )

                for actor_output, data_item, tree_descriptor in active_root_outputs:
                    event_id_state = event_id_states_by_tree.setdefault(
                        tree_descriptor["tree_name"], {"next_event_id": 0}
                    )
                    source_tokens = {}
                    chunk_tokens = {}

                    def record_source_progress(
                        state, merge_source, source_entries=None
                    ):
                        if self.profiler.enabled is False:
                            return
                        source_path = Path(merge_source["root_output_path"])
                        source_key = str(source_path.resolve())
                        metadata = _output_contribution_metadata(
                            actor_output,
                            merge_source.get("job_index"),
                            coordinator="root",
                            phase="finalize",
                            source_path=source_key,
                            source_bytes=(
                                source_path.stat().st_size
                                if source_path.exists()
                                else None
                            ),
                            target_path=str(output_path),
                            tree_name=tree_descriptor["tree_name"],
                        )
                        if state == "started":
                            if self.diagnostic_chunk_profiling:
                                metadata.update(
                                    _diagnostic_prefixed_process_memory_snapshot(
                                        "start"
                                    )
                                )
                            source_tokens[source_key] = self.profiler.start(
                                "output_contribution", metadata=metadata
                            )
                            return
                        token = source_tokens.pop(source_key, None)
                        completion_metadata = {"source_entries": source_entries}
                        if self.diagnostic_chunk_profiling:
                            completion_metadata.update(
                                _diagnostic_prefixed_process_memory_snapshot("end")
                            )
                        self.profiler.stop(
                            token,
                            outcome=("completed" if state == "completed" else "failed"),
                            metadata=completion_metadata,
                        )

                    def record_chunk_progress(
                        state,
                        phase,
                        merge_source,
                        chunk_index,
                        metadata=None,
                    ):
                        # DIAGNOSTIC ONLY: high-cardinality per-chunk records are
                        # emitted solely for the ROOT memory profiling study.
                        if (
                            not self.diagnostic_chunk_profiling
                            or not self.profiler.enabled
                        ):
                            return
                        source_path = Path(merge_source["root_output_path"])
                        token_key = (str(source_path.resolve()), chunk_index, phase)
                        chunk_metadata = {
                            "job_index": merge_source.get("job_index"),
                            "chunk_index": chunk_index,
                            "chunk_phase": phase,
                            "source_path": str(source_path.resolve()),
                            **(metadata or {}),
                        }
                        if state == "started":
                            chunk_metadata.update(
                                _diagnostic_prefixed_process_memory_snapshot(
                                    "start"
                                )
                            )
                            chunk_tokens[token_key] = self.profiler.start(
                                f"diagnostic_chunk.{phase}",
                                metadata=chunk_metadata,
                            )
                            return
                        chunk_metadata.update(_diagnostic_process_memory_snapshot())
                        token = chunk_tokens.pop(token_key, None)
                        self.profiler.stop(
                            token,
                            outcome=("completed" if state == "completed" else "failed"),
                            metadata=chunk_metadata,
                        )

                    data_item.stream_write_merged_root(
                        output_path,
                        metadata_path=actor_output.get_metadata_path(),
                        writer=writer,
                        event_id_state=event_id_state,
                        timing=timing,
                        source_progress_callback=(
                            record_source_progress if self.profiler.enabled else None
                        ),
                        step_size=self.chunk_size,
                        decompression_executor=decompression_executor,
                        chunk_progress_callback=(
                            record_chunk_progress
                            if self.diagnostic_chunk_profiling
                            else None
                        ),
                        release_chunk_references=(
                            self.diagnostic_release_chunk_references
                        ),
                    )
            finally:
                started_at = time.perf_counter() if timing is not None else None
                diagnostic_close_token = None
                if self.diagnostic_chunk_profiling and self.profiler.enabled:
                    # DIAGNOSTIC ONLY: distinguish writer-owned live memory from
                    # allocator pages retained after individual chunks.
                    diagnostic_close_token = self.profiler.start(
                        "diagnostic_writer.close",
                        metadata=_diagnostic_prefixed_process_memory_snapshot("start"),
                    )
                try:
                    writer.close()
                except BaseException:
                    if diagnostic_close_token is not None:
                        self.profiler.stop(
                            diagnostic_close_token,
                            outcome="failed",
                            metadata=_diagnostic_prefixed_process_memory_snapshot(
                                "end"
                            ),
                        )
                    raise
                else:
                    if diagnostic_close_token is not None:
                        self.profiler.stop(
                            diagnostic_close_token,
                            metadata=_diagnostic_prefixed_process_memory_snapshot(
                                "end"
                            ),
                        )
                if timing is not None:
                    timing["close_s"] += time.perf_counter() - started_at
                    if output_path.exists():
                        timing["output_bytes"] += output_path.stat().st_size
