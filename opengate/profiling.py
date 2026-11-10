"""Lightweight hierarchical profiling for GATE execution workflows."""

from __future__ import annotations

import json
import os
import socket
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path


PROFILE_SCHEMA_VERSION = 1


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _join_path(prefix, name):
    parts = [str(part).strip(".") for part in (prefix, name) if part]
    return ".".join(part for part in parts if part)


def profile_method(name=None):
    """Measure an instance method through ``self.profiler`` when enabled."""

    def decorate(method):
        measurement_name = name or method.__name__

        @wraps(method)
        def wrapped(self, *args, **kwargs):
            if self.profiler.enabled is False:
                return method(self, *args, **kwargs)
            with self.profiler.measure(measurement_name):
                return method(self, *args, **kwargs)

        return wrapped

    return decorate


class _ProfilerInventory:
    def __init__(self, enabled=False, name=None, metadata=None):
        self.enabled = bool(enabled)
        self.name = name
        self.metadata = dict(metadata or {})
        self.records = []
        self.values = {}
        self.active = {}
        self.record_ids = set()
        self.lock = threading.RLock()

    def __getstate__(self):
        state = dict(self.__dict__)
        # Active timers belong to the current process and cannot cross a spawn.
        state["active"] = {}
        state.pop("lock", None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.lock = threading.RLock()


class Profiler:
    """Collect named timings and scalar values in a serializable inventory.

    Profilers are disabled by default. Scoped profilers share one backing
    inventory in a process and prepend their scope to record and value paths.
    Snapshots crossing process boundaries are merged explicitly.
    """

    def __init__(
        self,
        name=None,
        *,
        enabled=False,
        metadata=None,
        _inventory=None,
        _prefix="",
    ):
        self._inventory = _inventory or _ProfilerInventory(
            enabled=enabled,
            name=name,
            metadata=metadata,
        )
        self._prefix = str(_prefix).strip(".")

    @property
    def name(self):
        return self._inventory.name

    @property
    def enabled(self):
        return self._inventory.enabled

    @enabled.setter
    def enabled(self, value):
        self._inventory.enabled = bool(value)

    @property
    def prefix(self):
        return self._prefix

    def enable(self):
        self.enabled = True
        return self

    def disable(self):
        self.enabled = False
        return self

    @property
    def has_data(self):
        inventory = self._inventory
        return bool(inventory.records or inventory.values or inventory.active)

    def scope(self, prefix):
        return Profiler(
            _inventory=self._inventory,
            _prefix=_join_path(self._prefix, prefix),
        )

    def start(self, name, metadata=None):
        if self.enabled is False:
            return None
        token = uuid.uuid4().hex
        active_record = {
            "record_id": token,
            "path": _join_path(self._prefix, name),
            "started_at": _utc_now(),
            "_started_perf_counter": time.perf_counter(),
            "hostname": socket.gethostname(),
            "process_id": os.getpid(),
            "thread_id": threading.get_ident(),
            "metadata": dict(metadata or {}),
        }
        with self._inventory.lock:
            self._inventory.active[token] = active_record
        return token

    def stop(self, token, *, outcome="completed", metadata=None):
        if token is None:
            return None
        with self._inventory.lock:
            try:
                active_record = self._inventory.active.pop(token)
            except KeyError as error:
                raise KeyError(
                    f"Unknown or already stopped profiler token: {token}"
                ) from error
            finished_perf_counter = time.perf_counter()
            record = {
                key: value
                for key, value in active_record.items()
                if key != "_started_perf_counter"
            }
            record.update(
                {
                    "finished_at": _utc_now(),
                    "duration_s": finished_perf_counter
                    - active_record["_started_perf_counter"],
                    "outcome": outcome,
                }
            )
            if metadata:
                record["metadata"].update(metadata)
            self._inventory.records.append(record)
            self._inventory.record_ids.add(record["record_id"])
            return dict(record)

    @contextmanager
    def measure(self, name, metadata=None):
        token = self.start(name, metadata=metadata)
        try:
            yield token
        except BaseException as error:
            self.stop(
                token,
                outcome="failed",
                metadata={"error_type": type(error).__name__},
            )
            raise
        else:
            self.stop(token)

    def set_value(self, name, value):
        if self.enabled is False:
            return
        path = _join_path(self._prefix, name)
        with self._inventory.lock:
            self._inventory.values[path] = value

    def get_value(self, name, default=None):
        path = _join_path(self._prefix, name)
        return self._inventory.values.get(path, default)

    def to_dictionary(self, *, require_complete=True):
        with self._inventory.lock:
            if require_complete and self._inventory.active:
                active_paths = sorted(
                    record["path"] for record in self._inventory.active.values()
                )
                raise RuntimeError(
                    "Cannot create a complete profiler snapshot while timers are "
                    f"active: {active_paths}"
                )
            payload = {
                "schema_version": PROFILE_SCHEMA_VERSION,
                "name": self.name,
                "enabled": self.enabled,
                "metadata": dict(self._inventory.metadata),
                "records": [dict(record) for record in self._inventory.records],
                "values": dict(self._inventory.values),
            }
            if require_complete is False:
                payload["active"] = [
                    {
                        key: value
                        for key, value in record.items()
                        if key != "_started_perf_counter"
                    }
                    for record in self._inventory.active.values()
                ]
        # Validate the public contract before returning the snapshot.
        json.dumps(payload)
        return payload

    def to_json_string(self, *, require_complete=True, **kwargs):
        kwargs.setdefault("indent", 2)
        kwargs.setdefault("sort_keys", True)
        return json.dumps(
            self.to_dictionary(require_complete=require_complete),
            **kwargs,
        )

    def to_json_file(self, path, *, require_complete=True):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with temporary_path.open("w", encoding="utf-8") as stream:
            stream.write(self.to_json_string(require_complete=require_complete))
            stream.write("\n")
        os.replace(temporary_path, path)
        return path

    def merge(self, snapshot, *, prefix=None):
        if isinstance(snapshot, Profiler):
            snapshot = snapshot.to_dictionary(require_complete=False)
        if snapshot.get("schema_version") != PROFILE_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported profiler schema version: "
                f"{snapshot.get('schema_version')}"
            )
        with self._inventory.lock:
            for record in snapshot.get("records", []):
                record = dict(record)
                record_id = record["record_id"]
                if record_id in self._inventory.record_ids:
                    continue
                record["path"] = _join_path(prefix, record["path"])
                self._inventory.records.append(record)
                self._inventory.record_ids.add(record_id)
            for path, value in snapshot.get("values", {}).items():
                target_path = _join_path(prefix, path)
                existing = self._inventory.values.get(target_path, value)
                if existing != value:
                    raise ValueError(
                        f"Conflicting profiler value for '{target_path}': "
                        f"{existing!r} versus {value!r}."
                    )
                self._inventory.values[target_path] = value
        return self

    @classmethod
    def from_dictionary(cls, payload):
        profiler = cls(
            name=payload.get("name"),
            enabled=payload.get("enabled", False),
            metadata=payload.get("metadata"),
        )
        profiler.merge(payload)
        return profiler

    @classmethod
    def from_json_file(cls, path):
        with Path(path).open(encoding="utf-8") as stream:
            return cls.from_dictionary(json.load(stream))


class Profilable:
    """Mixin for runtime objects that expose a profiler by default."""

    def initialize_profiler(self, name=None):
        if name is None:
            name = getattr(self, "name", None) or type(self).__name__
        self.profiler = Profiler(
            name=name,
            metadata={"class": type(self).__name__},
        )
        return self.profiler

    def attach_profiler(self, profiler, *, scope=None):
        target = profiler.scope(scope) if scope else profiler
        current = getattr(self, "profiler", None)
        if current is not None and current is not target and current.has_data:
            target.merge(current.to_dictionary(require_complete=False))
        self.profiler = target
        return self.profiler
