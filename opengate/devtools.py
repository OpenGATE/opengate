import pkgutil
import os
import inspect
import importlib
from typing import get_type_hints
from functools import partial
from pathlib import Path

import opengate_core


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
        if any([e in module_name for e in exclude_modules_packages]):
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


def print_g4units_dict_string():
    dict_content_str = ""
    already_processed_keys = []
    for t in opengate_core.G4UnitDefinition.GetUnitsTable():
        for a in t.GetUnitsList():
            if str(a.GetName()) not in already_processed_keys:
                dict_content_str += f"    '{str(a.GetName())}': {a.GetValue()}, \n"
                already_processed_keys.append(str(a.GetName()))
            if str(a.GetSymbol()) not in already_processed_keys:
                dict_content_str += f"    '{str(a.GetSymbol())}': {a.GetValue()}, \n"
                already_processed_keys.append(str(a.GetSymbol()))
    print("g4_units = Box({\n" + f"{dict_content_str}" + "})")


def generate_pyi_for_module(module, output_dir):
    # Ensure output_dir exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all classes defined in the module
    classes = inspect.getmembers(module, inspect.isclass)

    module_name = module.__name__.split(".")[-1]  # Just the module name, not full path
    output_path = os.path.join(output_dir, f"{module_name}.pyi")
    with open(output_path, "w") as stub_file:
        for class_name, cls in classes:
            # Skip classes not defined in the module itself (e.g., imported ones)
            if cls.__module__ != module.__name__:
                continue

            # Write the class definition
            stub_file.write(f"class {class_name}:\n")

            # Get manual type hints using get_type_hints
            type_hints = get_type_hints(cls)

            # Write properties with manual type hints
            for name, hint in type_hints.items():
                stub_file.write(f"    {name}: {hint.__name__}\n")

            # Get dynamically added attributes
            for name, value in cls.__dict__.items():
                if name not in type_hints and not name.startswith("_"):
                    stub_file.write(f"    {name}: {type(value).__name__}\n")

            # Add a newline between classes
            stub_file.write("\n")


def walk_package_and_generate_pyi(
    package_name, package_dir, output_dir, exclude_modules_packages=None
):
    """
    Walk through the package and generate pyi files for all modules.
    - package_name: The name of the package (e.g., 'mypackage').
    - package_dir: The root directory of the package (e.g., './mypackage').
    - output_dir: The directory where the .pyi files should be written.
    """

    if exclude_modules_packages is None:
        exclude_modules_packages = tuple()

    for root, _, files in os.walk(package_dir):

        root_path = Path(root)

        # Calculate the relative path of the current directory to package_dir
        relative_path = root_path.relative_to(package_dir)

        # Calculate the corresponding output directory
        current_output_dir = output_dir / relative_path

        # For each .py file in the directory (ignoring __init__.py for now)
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                # Get the module name relative to the package root
                module_path = root_path / file
                relative_module_path = module_path.relative_to(package_dir)
                # relative_module_path = os.path.relpath(module_path, package_dir)
                module_name = (
                    relative_module_path.with_suffix("").as_posix().replace("/", ".")
                )
                # module_name = relative_module_path.replace(os.sep, ".").rstrip(".py")

                if any([e in module_name for e in exclude_modules_packages]):
                    continue

                # Import the module dynamically
                try:
                    module = importlib.import_module(f"{package_name}.{module_name}")
                    # Generate the .pyi file for the module
                    generate_pyi_for_module(module, current_output_dir)
                    print(f"Generated .pyi for module: {module_name}")
                except Exception as e:
                    print(
                        f"Failed to generate .pyi for module: {module_name}. Error: {e}"
                    )

        # Generate __init__.pyi for directories
        if "__init__.py" in files:
            init_module_name = relative_path.as_posix().replace("/", ".") + ".__init__"
            try:
                init_module = importlib.import_module(
                    f"{package_name}.{init_module_name}"
                )
                generate_pyi_for_module(init_module, current_output_dir)
                print(f"Generated __init__.pyi for module: {init_module_name} (init)")
            except Exception as e:
                print(
                    f"Failed to generate __init__.pyi for module: {init_module_name}. Error: {e}"
                )


generate_pyi_files_for_opengate = partial(
    walk_package_and_generate_pyi,
    package_name="opengate",
    exclude_modules_packages=("tests.src",),
)
