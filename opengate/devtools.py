import inspect
import pkgutil
import importlib

from .base import GateObject

def check_classes_in_current_package(attribute_name, package_name=None,
                                     attribute_type=None, sub_package_name=None, inherits_from=None):
    """
    Checks for the presence of a certain attribute type (attribute, property, or method)
    in all classes of the current package, optionally restricted to a sub-package.

    :param attribute_name: Name of the attribute to check.
    :param attribute_type: Type of the attribute to check for (attribute, property, method).
    :param sub_package_name: Name of the sub-package to restrict the check to (optional).
    """
    if package_name is None:
        # Get the current package's name
        package_name = __package__

    if not package_name:
        raise RuntimeError("This script needs to be part of a package to work.")

    # If a sub-package is provided, use it as the base package
    if sub_package_name:
        package_name = f"{package_name}.{sub_package_name}"

    if inherits_from:
        instance_of_module = importlib.import_module('.'.join(inherits_from.split('.')[:-1]))
        instance_of_class_name = inherits_from.split('.')[-1]
        instance_of_class = [c for k, c in inspect.getmembers(instance_of_module) if k == instance_of_class_name][0]
        print(instance_of_class)

    # Import the target package (current or sub-package)
    package = importlib.import_module(package_name)

    warnings = []
    # Iterate through all modules in the specified package
    for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if not is_pkg:
            module = importlib.import_module(module_name)
            # Iterate through all members of the module
            for name, obj in inspect.getmembers(module):
                # Check if the object is a class
                if inspect.isclass(obj):
                    if inherits_from is not None and instance_of_class not in obj.mro():
                        continue
                    # Check if the class has the desired attribute
                    if hasattr(obj, attribute_name):
                        attribute = getattr(obj, attribute_name)
                        if attribute_type is not None:
                            found_attribute_type = get_attribute_type(attribute)
                            if found_attribute_type != attribute_type:
                                base_msg = (f"Class {obj.__name__} in module {module_name} "
                                            f"has the attribute '{attribute_name}', "
                                            "but it is not a ")
                                if found_attribute_type in ('method', 'property'):
                                    warnings.append(base_msg + f'{attribute_type}.')
                                elif found_attribute_type == 'plain':
                                    warnings.append(base_msg + 'plain attribute.')
                    else:
                        warnings.append(
                            f"Class {obj.__name__} in module {module_name} "
                            f"does NOT have the attribute '{attribute_name}'.")
    return warnings


def get_attribute_type(attribute):
    if callable(attribute):
        return 'method'
    elif isinstance(attribute, property):
        return 'property'
    else:
        return 'plain'

