from ..exception import fatal


def get_table_column(table, column_name):
    try:
        columns = table.cols
        try:
            return getattr(columns, column_name)
        except AttributeError:
            fatal(f"No column found for attribute {column_name}")
    except AttributeError:
        fatal(f"Incompatible input for 'table'. Should be a table. ")


def get_table_column_names(table):
    return table.cols._v_colnames


def get_node_name(node):
    return node._v_name


def set_node_name(node, name):
    node._v_name = name


def get_node_path(node, strip_leading_slash=False):
    p = node._v_pathname
    if strip_leading_slash is True:
        p = p.lstrip("/")
    return p


def get_group_name(group):
    return get_node_name(group)


def get_nodes_in_group(group, node_type=None, node_name=None, condition_functions=None):
    all_nodes = [n for n in group._f_iter_nodes()]
    return filter_nodes(all_nodes, node_type, node_name, condition_functions)


def filter_nodes(nodes, node_type=None, node_name=None, condition_functions=None):
    conditions = []
    if node_type is not None:
        conditions.append(lambda _n: isinstance(_n, node_type))
    if node_name is not None:
        conditions.append(lambda _n: get_node_name(_n) == node_name)
    if condition_functions is not None:
        conditions.extend(tuple(condition_functions))
    selected_nodes = []
    for n in nodes:
        if all([c(n) is True for c in conditions]):
            selected_nodes.append(n)
    return selected_nodes


def get_parent(node):
    return node._v_parent


def create_hard_links_to_nodes_in_group(where_group, target_group):
    file_handle = where_group._v_file
    for n in target_group._f_iter_nodes():
        print(f"where_group: {where_group}")
        print(f"node name: {get_node_name(n)}")
        print(f"n: {n}")
        file_handle.create_hard_link(where_group, get_node_name(n), target=n)


def get_create_function(file_handle, which):
    if which in ("table", "Table"):
        create_func = file_handle.create_table
    elif which in ("array", "Array"):
        create_func = file_handle.create_array
    elif which in ("carray", "Carray"):
        create_func = file_handle.create_carray
    elif which in ("earray", "Earray"):
        create_func = file_handle.create_earray
    elif which in ("group", "Group"):
        create_func = file_handle.create_group
    else:
        fatal(
            f"Unkown kind of output structure '{which}'. "
            f"Known structures are table, array, carray, earray, group"
        )
    return create_func
