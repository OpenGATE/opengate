from functools import wraps

from opengate.physics.helpers_physics import available_additional_physics_lists


# decorator to check if class attribute is None
def requires(attribute):
    def decorator(func):
        @wraps(func)
        def _with_check(self, *args, **kwargs):
            if getattr(self, decorator.attribute) is None:
                raise Exception(
                    f"Method {func.__name__} of class {type(self)} requires {decorator.attribute} to be set, but it is None."
                )
            return func(self, *args, **kwargs)

        return _with_check

    decorator.attribute = attribute
    return decorator
