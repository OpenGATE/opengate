import json
import numpy as np


class GateJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "as_dictionary"):
            return obj.as_dictionary()
        elif isinstance(obj, np.ndarray):
            return {
                "__ndarray__": obj.tolist(),
                "dtype": str(obj.dtype),
                "shape": obj.shape,
            }
        else:
            return super().default(obj)


def json_obj_hook(dct):
    """
    Decodes a previously encoded numpy ndarray
    with proper shape and dtype
    :param dct: (dict) json encoded ndarray
    :return: (ndarray) if input was an encoded ndarray
    """
    if isinstance(dct, dict) and "__ndarray__" in dct:
        return np.array(dct["__ndarray__"], dct["dtype"]).reshape(dct["shape"])
    else:
        return dct


# Overload dump/load from json
def dumps_json(*args, **kwargs):
    kwargs.setdefault("cls", GateJSONEncoder)
    return json.dumps(*args, **kwargs)


def loads_json(*args, **kwargs):
    kwargs.setdefault("object_hook", json_obj_hook)
    return json.loads(*args, **kwargs)


def dump_json(*args, **kwargs):
    kwargs.setdefault("cls", GateJSONEncoder)
    return json.dump(*args, **kwargs)


def load_json(*args, **kwargs):
    kwargs.setdefault("object_hook", json_obj_hook)
    return json.load(*args, **kwargs)
