import inspect
import pkgutil
import importlib


def apply_class_check_to_package(
    check_func,
    package_name=None,
    sub_package_name=None,
    exclude_modules_packages=None,
    inherits_from=None,
    func_kwargs=None,
):
    """
    Checks for the presence of a certain attribute type (attribute, property, or method)
    in all classes of the current package, optionally restricted to a sub-package.

    :param check_func: Function to which the class is passed as an argument. Should return a warning string or None.
    :param attribute_name: Name of the attribute to check.
    :param attribute_type: Type of the attribute to check for (plain, property, method).
    :param sub_package_name: Name of the sub-package to restrict the check to (optional).
    :param inherits_from: Restrict the chck to classes that inherit from the class provided as inherits_from.
        Needs to be a qualified name, e.g. inherits_from=opengate.actors.ActorBase
    """
    if func_kwargs is None:
        func_kwargs = {}
    if package_name is None:
        # Get the current package's name
        package_name = __package__

    if not package_name:
        raise RuntimeError(
            "You need to either provide a package name or "
            "this script needs to be part of a package to work."
        )

    # If a sub-package is provided, use it as the base package
    if sub_package_name:
        package_name = f"{package_name}.{sub_package_name}"

    if exclude_modules_packages is None:
        exclude_modules_packages = tuple()

    if inherits_from:
        instance_of_module = importlib.import_module(
            ".".join(inherits_from.split(".")[:-1])
        )
        instance_of_class_name = inherits_from.split(".")[-1]
        instance_of_class = [
            c
            for k, c in inspect.getmembers(instance_of_module)
            if k == instance_of_class_name
        ][0]

    # Import the target package (current or sub-package)
    package = importlib.import_module(package_name)

    warnings = []
    # Iterate through all modules in the specified package
    for xxx, module_name, is_pkg in pkgutil.walk_packages(
        package.__path__, package.__name__ + "."
    ):
        skip_this = False
        for e in exclude_modules_packages:
            if e in module_name:
                skip_this = True
                break
        if skip_this is True:
            continue
        if not is_pkg:
            module = importlib.import_module(module_name)
            # Iterate through all members of the module
            for name, obj in inspect.getmembers(module):
                # Check if the object is a class
                if inspect.isclass(obj):
                    try:
                        if (
                            inherits_from is not None
                            and instance_of_class not in obj.mro()
                        ):
                            continue
                        w = check_func(obj, **func_kwargs)
                        if w is not None:
                            warnings.append(w)
                    except TypeError:
                        print(f"Could not check class {repr(obj)}")
                        continue
    return warnings


def get_attribute_type(attribute):
    if callable(attribute):
        return "method"
    elif isinstance(attribute, property):
        return "property"
    else:
        return "plain"


def check_if_class_has_attribute(cls, attribute_name=None, attribute_type=None):
    """Check if the class has the desired attribute"""
    if attribute_name is None:
        raise ValueError("kwarg 'attribute_name' is required. ")
    warning = None
    if hasattr(cls, attribute_name):
        attribute = getattr(cls, attribute_name)
        if attribute_type is not None:
            found_attribute_type = get_attribute_type(attribute)
            if found_attribute_type != attribute_type:
                base_msg = (
                    f"Class {cls.__name__} in module {cls.__module__} "
                    f"has the attribute '{attribute_name}', "
                    "but it is not a "
                )
                if found_attribute_type in ("method", "property"):
                    warning = base_msg + f"{attribute_type}."
                elif found_attribute_type == "plain":
                    warning = base_msg + "plain attribute."
    else:
        warning = (
            f"Class {cls.__name__} in module {cls.__module__} "
            f"does NOT have the attribute '{attribute_name}'."
        )
    return warning


def find_unprocessed_gateobject_classes():
    def check_if_class_has_been_processed(cls):
        if cls.has_been_processed():
            return None
        else:
            return repr(cls)

    print(
        "Checking if there are any classes in opengate that inherit from GateObject "
        "and that are not properly processed by a call to process_cls() ..."
    )
    return set(
        apply_class_check_to_package(
            check_if_class_has_been_processed,
            package_name="opengate",
            inherits_from="opengate.base.GateObject",
            exclude_modules_packages=(
                "opengate.bin",
                "opengate.tests.src",
                "opengate.postprocessors",
            ),
        )
    )
