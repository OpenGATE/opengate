from functools import wraps

from .helpers import fatal, warning


# decorator template to check if class attribute is None
def requires(attribute, mode="fatal"):
    def decorator(func):
        @wraps(func)
        def _with_check(self, *args, **kwargs):
            if getattr(self, decorator.attribute) is None:
                msg = f"Method {func.__name__} of class {type(self)} requires {decorator.attribute} to be set, but it is None."
                if decorator.mode == "fatal":
                    fatal(msg)
                elif decorator.mode == "warning":
                    warning(msg)
            return func(self, *args, **kwargs)

        return _with_check

    decorator.attribute = attribute
    decorator.mode = mode

    return decorator


def requires_fatal(attribute):
    return requires(attribute, mode="fatal")


def requires_warning(attribute):
    return requires(attribute, mode="warning")
