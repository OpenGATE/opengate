"""Execution controllers shared by monolithic and multi-job workflows."""

from datetime import datetime, timezone
import uuid

from .profiling import Profilable, profile_method


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


class ExecutionController(Profilable):
    """Base class for one concrete execution of a simulation configuration."""

    def __init__(
        self,
        simulation,
        *,
        profiling=False,
        profiler=None,
        name=None,
    ):
        if profiling is not None and not isinstance(profiling, bool):
            raise TypeError(
                f"{type(self).__name__} expects profiling= to be True, False, "
                f"or None; received {profiling!r}."
            )
        self.simulation = simulation
        self.execution_id = uuid.uuid4().hex
        self.started_at = None
        self.finished_at = None
        self._stage = "initialized"
        self._status = {"error": None}

        self.initialize_profiler(name=name or type(self).__name__)
        if profiler is not None:
            self.attach_profiler(profiler)
        if profiling is not None:
            self.profiler.enabled = profiling

    @property
    def stage(self):
        return self._stage

    @property
    def status(self):
        return self._status

    def has_finished(self):
        return self.stage in ("completed", "merged", "cleaned", "failed")

    def has_failed(self):
        return self.stage == "failed"

    def _mark_started(self):
        self.started_at = _utc_now()
        self._stage = "running"

    def _mark_completed(self):
        self.finished_at = _utc_now()
        self._stage = "completed"

    def _set_error(self, error):
        self.finished_at = _utc_now()
        self._status["error"] = f"{type(error).__name__}: {error}"
        self._stage = "failed"


class MonolithicRunController(ExecutionController):
    """Synchronous controller for one ordinary GATE simulation execution."""

    def __init__(
        self,
        simulation,
        *,
        start_new_process=False,
        profiling=False,
        profiler=None,
    ):
        super().__init__(
            simulation,
            profiling=profiling,
            profiler=profiler,
        )
        self.start_new_process = bool(start_new_process)

    @profile_method("execute")
    def execute(self):
        if self.stage != "initialized":
            raise RuntimeError(
                "MonolithicRunController.execute() can only be called once."
            )
        self._mark_started()
        try:
            self.simulation._execute_monolithic(
                start_new_process=self.start_new_process,
                profiler=self.profiler.scope("simulation"),
            )
        except Exception as error:
            self._set_error(error)
            raise
        self._mark_completed()
        return self

    def wait(self, *args, **kwargs):
        """Return immediately because monolithic execution is synchronous."""
        return self
