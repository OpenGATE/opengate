import json
import numpy as np
from pathlib import Path, PurePath

from .exception import fatal

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
            return {"__pathlib_path__": PurePath(obj).parts}
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
        obj = Path(input["__pathlib_path__"][0])
        for p in input["__pathlib_path__"][1:]:
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
