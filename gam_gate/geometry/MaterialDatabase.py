from .MaterialBuilder import *


class MaterialDatabase:
    """
        Manage a list of Geant4 materials and elements.
        Read the data from a txt file (compatible with Gate database)

    """

    def __init__(self, filename, material_databases):
        self.filename = filename
        self.materials = {}
        self.elements = {}
        self.material_builders = {}
        self.element_builders = {}
        self.current_section = 'None'
        self.material_databases = material_databases
        self.read_builders()

    def __del__(self):
        pass

    def read_builders(self):
        f = open(self.filename, "r")
        line = f.readline()
        while line:
            self.read_item(f, line)
            line = f.readline()

    def read_item(self, f, line):
        line = line.strip()
        if len(line) < 1:
            return
        if line[0] == '#':
            return
        # check if the current section change
        w = line.split()[0]
        if w == '[Elements]':
            self.current_section = 'element'
            return
        if w == '[Materials]':
            self.current_section = 'material'
            return
        if not self.current_section:
            gam.fatal(f'Error while reading the file {self.filename}, '
                      f'current section is {self.current_section}. '
                      f'File must start with [Elements] or [Materials]')
        b = MaterialBuilder(self)
        if self.current_section == 'element':
            b.read_element(f, line)
            self.element_builders[b.name] = b
        if self.current_section == 'material':
            b.read_material(f, line)
            self.material_builders[b.name] = b

    def FindOrBuildMaterial(self, material):
        if material in self.materials:
            return self.materials[material]
        if material not in self.material_builders:
            return None
        b = self.material_builders[material]
        bm = b.build()
        self.materials[material] = bm
        return bm

    def FindOrBuildElement(self, element, loop=True):
        if element in self.elements:
            return self.elements[element]
        if element not in self.element_builders:
            if not loop:
                return None
            for n in self.material_databases:
                if n == self.filename:
                    continue
                db = self.material_databases[n]
                e = db.FindOrBuildElement(element, False)
                if e:
                    return e
            gam.fatal(f'Cannot find or build {element}')
            return None
        b = self.element_builders[element]
        be = b.build()
        self.elements[element] = be
        return be

    def dump_materials(self, level):
        if level == 0:
            return list(self.material_builders.keys())
        s = ''
        for m in self.material_builders.values():
            s = s + str(m) + '\n'
        return s
