import copy
from .sources.builders import source_builders, source_type_names
from .actors.builders import filter_builders, filter_type_names
from .exception import fatal


element_builders = {
    "Source": source_builders,
    "Filter": filter_builders,
}


def get_element_class(element_type, type_name):
    """
    Return the class of the given type_name (in the element_type list)
    """
    elements = None
    if element_type == "Source":
        elements = source_type_names
    if element_type == "Filter":
        elements = filter_type_names
    if not elements:
        fatal(
            f"Error, element_type={element_type} is   unknown. Use Volume, Source or Actor."
        )
    for e in elements:
        # check the class has type_name
        if not hasattr(e, "type_name"):
            fatal(
                f'Error, the class {e.__name__} *must* have a static attribute called "type_name"'
            )
        # is the type the one we are looking ?
        if e.type_name == type_name:
            return e
    s = [x.type_name for x in elements]
    fatal(
        f'Error {element_type}: the type "{type_name}" is unknown. Known types are {s}'
    )


def get_builder(element_type, type_name):
    """
    Return a function that build an element of the class type_name
    Check everything first.
    """
    # get type of element builder
    if element_type not in element_builders:
        fatal(
            f"The element type: {element_type} is unknown.\n"
            f"Known element types are {element_builders.keys()}"
        )
    builders = element_builders[element_type]
    # get builder
    if type_name not in builders:
        fatal(
            f"The element type: {type_name} is unknown.\n"
            f"Known type names are {builders.keys()}"
        )
    builder = builders[type_name]
    return builder


def new_element(user_info, simulation=None):
    """
    Create a new element (Volume, Source, Actor, Filter), according to the type name
    - use the element_builders to find the class to build
    - create a new element, with the name as parameter to the constructor
    - initialize the default list of keys in the user_info
    - set a pointer to the Simulation object
    """
    builder = get_builder(user_info.element_type, user_info.type_name)
    # build (create the object)
    e = builder(user_info)
    # set the simulation pointer
    e.set_simulation(simulation)
    return e
