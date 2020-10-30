import gam

element_builders = {
    'Volume': gam.volume_builders,
    'Source': gam.source_builders,
    'Actor': gam.actor_builders,
    'SourcePosition': gam.source_position_builders
}


def new_element(element_type, type_name, name=None, simulation=None):
    # get type of element builder
    if element_type not in element_builders:
        gam.fatal(f'The element type: {element_type} is unknown.\n'
                  f'Known element types are {element_builders.keys()}')
    builders = element_builders[element_type]
    # get builder
    if type_name not in builders:
        gam.fatal(f'The element type: {type_name} is unknown.\n'
                  f'Known type names are {builders.keys()}')
    builder = builders[type_name]
    # build (create the object)
    e = builder(name)
    # initialize the list of required keys
    e.initialize_required_keys()
    # set the simulation pointer
    e.set_simulation(simulation)
    return e
