from functools import wraps
from .exception import fatal, warning


# decorator template to check if class attribute is None
# Inspired by this solution on StackExchange:
# https://stackoverflow.com/questions/22271923/python-decorator-arguments-with-syntax
# Logic: the outer function requires creates the decorator function
# which checks for a specific attribute in a class
# So: requires('physics_engine', mode='fatal') generates a function with an in-built
# variable decorator.attribute='physics_engine'
# so that @requires('physics_engine', mode='fatal') can be used as a
# decorator for class methods which throws a fatal error when the class's attribute
# physics_engine is None. Obviously, this could also be achieved via an if-statement
# in the method. Using the decorator avoids boiler-plate code and increases readibility.
def requires_not_none(attribute, mode="fatal"):
    def decorator(func):
        # @wraps decorator copies the doc_string, function name, etc.
        # of the method 'func' over to the wrapper '_with_check'.
        # So: It informs python that 'func' is just wrapped,
        # but should still be treated as if it were 'func'
        @wraps(func)
        def _with_check(self, *args, **kwargs):
            if getattr(self, decorator.attribute) is None:
                msg = (
                    f"Method {func.__name__} of object {repr(self)} "
                    f"requires {decorator.attribute} to be set, but it is None."
                )
                if decorator.mode == "fatal":
                    fatal(msg)
                elif decorator.mode == "warning":
                    warning(msg)
            return func(self, *args, **kwargs)

        return _with_check

    decorator.attribute = attribute
    decorator.mode = mode
    return decorator


def requires_attribute(attribute, mode="fatal", msg=None):
    def decorator(func):
        # @wraps decorator copies the doc_string, function name, etc.
        # of the method 'func' over to the wrapper '_with_check'.
        # So: It informs python that 'func' is just wrapped,
        # but should still be treated as if it were 'func'
        @wraps(func)
        def _with_check(self, *args, **kwargs):
            if not hasattr(self, decorator.attribute):
                if decorator.msg is None:
                    msg = (
                        f"Method {func.__name__} of class {type(self)} requires {decorator.attribute} to exist, "
                        f"but it is part of this class."
                    )
                else:
                    msg = decorator.msg
                if decorator.mode == "fatal":
                    fatal(msg)
                elif decorator.mode == "warning":
                    warning(msg)
            return func(self, *args, **kwargs)

        return _with_check

    decorator.attribute = attribute
    decorator.mode = mode
    decorator.msg = msg
    return decorator


# Different flavors of the "requires" decorator
# with preset modes
def requires_fatal(attribute):
    return requires_not_none(attribute, mode="fatal")


def requires_warning(attribute):
    return requires_not_none(attribute, mode="warning")


def requires_attribute_fatal(attribute, msg=None):
    return requires_attribute(attribute, mode="fatal", msg=msg)
