import gam_gate as gam
from gam_gate import log


class FilterManager:
    """
    Manage all the Filters in the simulation
    """

    def __init__(self, simulation):
        self.simulation = simulation
        self.user_info_filters = {}
        self.filters = {}

    def __str__(self):
        v = [v.name for v in self.user_info_filters.values()]
        s = f'{" ".join(v)} ({len(self.user_info_filters)})'
        return s

    def __del__(self):
        pass

    def dump(self):
        n = len(self.user_info_filters)
        s = f'Number of filters: {n}'
        for Filter in self.user_info_filters.values():
            if n > 1:
                a = '\n' + '-' * 20
            else:
                a = ''
            a += f'\n {Filter}'
            s += gam.indent(2, a)
        return s

    def get_filter(self, name):
        if name not in self.filters:
            gam.fatal(f'The Filter {name} is not in the current '
                      f'list of Filters: {self.filters}')
        return self.filters[name]

    def add_filter(self, filter_type, name):
        # check that another element with the same name does not already exist
        gam.assert_unique_element_name(self.filters, name)
        # build it
        a = gam.UserInfo('Filter', filter_type, name)
        # append to the list
        self.user_info_filters[name] = a
        # return the info
        return a

    def initialize(self):
        print('filter init')
        for ui in self.user_info_filters.values():
            print(ui)
            filter = gam.new_element(ui, self.simulation)
            log.debug(f'Filter: initialize [{ui.type_name}] {ui.name}')
            filter.Initialize(ui)
            self.filters[ui.name] = filter
            print(filter)
