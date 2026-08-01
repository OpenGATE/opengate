import json
import time
import os
import sys
import numpy as np
from pathlib import Path, PurePath, PosixPath

from .exception import fatal, warning

import opengate_core as g4


class GateJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return {
                "__ndarray__": obj.tolist(),
                "__dtype__": str(obj.dtype),
                "__shape__": obj.shape,
            }
        elif isinstance(obj, Path):
            path_parts = PurePath(obj).parts
            if len(path_parts) == 0:
                # Path(".") round-trips to an empty ``parts`` tuple. Persist an
                # explicit current-directory marker so JSON reload can
                # reconstruct the same relative path instead of failing on an
                # empty list access.
                path_parts = (".",)
            return {"__pathlib_path__": path_parts}
        elif isinstance(obj, g4.G4BestUnit):
            return str(obj).split()
        elif hasattr(obj, "to_dictionary"):
            fatal(
                f"Implementation error: Serializer found GateObject named {obj.name}. "
                f"This should have been turned into a plain dictionary at this stage. "
            )
        else:
            return super().default(obj)


def json_obj_hook(input):
    """
    Decodes a previously encoded numpy ndarray
    with proper shape and dtype
    :param input: (dict) json encoded ndarray
    :return: (ndarray) if input was an encoded ndarray
    """
    if isinstance(input, dict) and "__ndarray__" in input:
        obj = np.array(input["__ndarray__"], input["__dtype__"]).reshape(
            input["__shape__"]
        )
    elif isinstance(input, dict) and "__pathlib_path__" in input:
        path_parts = input["__pathlib_path__"]
        if len(path_parts) == 0:
            path_parts = ["."]
        obj = Path(path_parts[0])
        for p in path_parts[1:]:
            obj /= p
    else:
        obj = input
    return obj


# Overload dump/load from json
def dumps_json(*args, **kwargs):
    kwargs.setdefault("cls", GateJSONEncoder)
    kwargs.setdefault("indent", 4)
    return json.dumps(*args, **kwargs)


def loads_json(*args, **kwargs):
    kwargs.setdefault("object_hook", json_obj_hook)
    return json.loads(*args, **kwargs)


def dump_json(*args, **kwargs):
    kwargs.setdefault("cls", GateJSONEncoder)
    kwargs.setdefault("indent", 4)
    return json.dump(*args, **kwargs)


def load_json(*args, **kwargs):
    kwargs.setdefault("object_hook", json_obj_hook)
    return json.load(*args, **kwargs)


def load_json_with_retry(path, attempts=5, delay_s=0.05, **kwargs):
    """Load JSON from a path with a short retry loop for transient read races."""
    kwargs.setdefault("object_hook", json_obj_hook)
    path = Path(path)
    last_error = None

    for attempt in range(attempts):
        try:
            with open(path, "r") as input_file:
                return json.load(input_file, **kwargs)
        except (FileNotFoundError, json.JSONDecodeError) as error:
            last_error = error
            if attempt == attempts - 1:
                raise
            time.sleep(delay_s)

    raise last_error


def _find_metaimage_payload_files(header_path, require_existing=True):
    payload_files = []
    try:
        with open(header_path, "r") as header_file:
            for line in header_file:
                if "=" not in line:
                    continue
                key, value = [part.strip() for part in line.split("=", 1)]
                if key != "ElementDataFile":
                    continue
                if value.upper() == "LOCAL":
                    return []
                payload_path = Path(value)
                if not payload_path.is_absolute():
                    payload_path = header_path.parent / payload_path
                if payload_path.is_file():
                    payload_files.append(payload_path.resolve())
                elif require_existing is False:
                    payload_files.append(payload_path.absolute())
                else:
                    warning(
                        f"MetaImage header '{header_path}' references payload file "
                        f"'{payload_path}', but that file does not exist."
                    )
                break
    except OSError as error:
        warning(f"Unable to inspect MetaImage header '{header_path}': {error}")
    return payload_files


def _rewrite_path_against_reference(path, reference_folder, path_mode):
    """Rewrite one path against a new simulation reference folder.

    Contract:
    - This helper only rewrites one path object/string.
    - It does not traverse dictionaries or user-info structures.
    - It does not copy, link, or otherwise materialize files.
    - It must not dereference symlinks when producing absolute paths.
    - It preserves the input type: ``Path`` stays ``Path``, ``str`` stays ``str``.

    ``path_mode="relative"`` prefers a path relative to ``reference_folder``.
    On platforms where no relative representation exists for the two paths
    (for example across drive letters on Windows), it falls back to a valid
    absolute path instead of failing. ``path_mode="absolute"`` expresses the
    same path as an absolute path anchored at ``reference_folder`` if needed,
    but preserves any symlink path components instead of collapsing them to
    their physical target location.
    """

    original_is_path = isinstance(path, Path)
    path_obj = Path(path)
    reference_folder = Path(reference_folder)

    if path_mode == "relative":
        try:
            rewritten_path = Path(
                os.path.relpath(
                    os.path.abspath(path_obj), os.path.abspath(reference_folder)
                )
            )
        except ValueError:
            # Windows cannot express a relative path across drive letters.
            # In that case, preserve a valid absolute authored path rather than
            # failing serialization of the whole simulation.
            rewritten_path = Path(os.path.abspath(path_obj))
    elif path_mode == "absolute":
        if path_obj.is_absolute():
            rewritten_path = Path(os.path.abspath(path_obj))
        else:
            rewritten_path = Path(os.path.abspath(reference_folder / path_obj))
    else:
        fatal(f"Unknown input-path rewrite mode '{path_mode}'.")

    if original_is_path:
        return rewritten_path
    return str(rewritten_path)


def _apply_path_modifier_recursively(value, scalar_path_modifier):
    """Recursively rewrite path-like scalars inside a serialized value.

    Contract:
    - This helper only traverses Python container structure: ``dict``, ``list``,
      ``tuple``, ``Path``, and ``str``.
    - It is pure: it returns a rewritten value and does not mutate the input.
    - It does not inspect GateObject metadata itself; higher-level callers stay
      responsible for selecting which user-info entries should be rewritten.
    - All scalar path semantics are delegated to ``scalar_path_modifier``. That
      callback receives one ``Path`` or ``str`` and must return one rewritten
      scalar of the same conceptual kind.
    """

    if isinstance(value, (Path, str)):
        return scalar_path_modifier(value)
    if isinstance(value, dict):
        return {
            k: _apply_path_modifier_recursively(v, scalar_path_modifier)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [
            _apply_path_modifier_recursively(v, scalar_path_modifier) for v in value
        ]
    if isinstance(value, tuple):
        return tuple(
            _apply_path_modifier_recursively(v, scalar_path_modifier) for v in value
        )
    return value


def _get_gate_object_class_from_dictionary(go_dict):
    """Resolve the Python class described by one serialized GateObject dict."""

    return getattr(sys.modules[go_dict["class_module"]], go_dict["object_type"])


def _collect_input_file_values_from_gate_object_dictionary(go_dict):
    """Collect serialized input-file references from one GateObject dictionary.

    This includes:
    - direct user-info entries marked ``is_input_file=True``
    - dynamic parametrisation entries whose underlying user-info definition is
      marked ``is_input_file=True``
    """

    from .base import DynamicGateObject, find_all_file_refs, _get_user_info_options

    collected_paths = []
    direct_input_file_names = set()
    for ui_name, ui_value in go_dict["user_info"].items():
        options = _get_user_info_options(
            ui_name, go_dict["object_type"], go_dict["class_module"]
        )
        if options.get("is_input_file") is True:
            direct_input_file_names.add(ui_name)
            collected_paths.extend(find_all_file_refs(ui_value))

    go_cls = _get_gate_object_class_from_dictionary(go_dict)
    if issubclass(go_cls, DynamicGateObject):
        class_dynamic_input_file_names = go_cls.get_dynamic_input_file_user_info_names()
    else:
        class_dynamic_input_file_names = set()

    dynamic_params = go_dict["user_info"].get("dynamic_params") or {}
    populated_dynamic_input_file_names = set()
    for parametrisation in dynamic_params.values():
        for ui_name in class_dynamic_input_file_names:
            if ui_name in parametrisation:
                populated_dynamic_input_file_names.add(ui_name)
                collected_paths.extend(find_all_file_refs(parametrisation[ui_name]))

    return (
        collected_paths,
        direct_input_file_names,
        populated_dynamic_input_file_names,
    )
