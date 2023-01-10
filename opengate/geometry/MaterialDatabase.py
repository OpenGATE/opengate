from .MaterialBuilder import *
from .ElementBuilder import *


class MaterialDatabase:
    """
    Manage a unique list of Geant4 materials and elements.
    The materials/elements are read in a DB txt file or in NIST.
    They are only build on demand, during the geometry Construct
    """

    def __init__(self):
        # list of all db filenames where to read material
        self.filenames = []
        # list of all read material (not build)
        self.material_builders = {}
        self.material_builders_by_filename = {}
        # list of all read element (not build)
        self.element_builders = {}
        self.element_builders_by_filename = {}
        # built materials
        self.g4_materials = {}
        # built elements
        self.g4_elements = {}
        # internal state when reading
        self.current_section = None
        self.current_filename = None
        # specific to NIST materials
        self.g4_NistManager = None
        self.nist_material_names = None
        self.nist_element_names = None

    def __del__(self):
        pass

    def read_from_file(self, filename):
        self.filenames.append(filename)
        self.current_filename = filename
        self.element_builders_by_filename[self.current_filename] = {}
        self.material_builders_by_filename[self.current_filename] = {}
        f = open(filename, "r")
        line = f.readline()
        while line:
            line = line.strip().replace("\t", " ")
            self.read_one_item(f, line)
            line = f.readline()

    def read_one_item(self, f, line):
        # skip empty lines
        if len(line) < 1:
            return
        # skip comment line
        if line[0] == "#":
            return
        # check if the current section change
        w = line.split()[0]
        if w == "[Elements]":
            self.current_section = "element"
            return
        if w == "[Materials]":
            self.current_section = "material"
            return
        if not self.current_section:
            gate.fatal(
                f"Error while reading the file {self.current_filename}, "
                f"current section is {self.current_section}. "
                f"File must start with [Elements] or [Materials]"
            )
        if self.current_section == "element":
            b = ElementBuilder(self)
            b.read(line)
            self.element_builders[b.name] = b
            self.element_builders_by_filename[self.current_filename][b.name] = b
        if self.current_section == "material":
            b = MaterialBuilder(self)
            b.read(f, line)
            self.material_builders[b.name] = b
            self.material_builders_by_filename[self.current_filename][b.name] = b

    def init_NIST(self):
        if self.g4_NistManager is None:
            self.g4_NistManager = g4.G4NistManager.Instance()
            self.nist_material_names = self.g4_NistManager.GetNistMaterialNames()
            self.nist_element_names = self.g4_NistManager.GetNistElementNames()
            self.material_builders_by_filename["NIST"] = self.nist_material_names
            self.element_builders_by_filename["NIST"] = self.nist_element_names

    def FindOrBuildMaterial(self, material_name):
        self.init_NIST()
        # return if already exist
        if material_name in self.g4_materials:
            return self.g4_materials[material_name]
        # we build and store the G4 material if not
        if material_name in self.nist_material_names:
            bm = self.g4_NistManager.FindOrBuildMaterial(material_name)
            self.g4_materials[material_name] = bm
            return bm
        if material_name not in self.material_builders:
            gate.fatal(f'Cannot find nor build material named "{material_name}"')
        bm = self.material_builders[material_name].build()
        self.g4_materials[material_name] = bm
        return bm

    def FindOrBuildElement(self, element_name):
        self.init_NIST()
        # return if already exist
        if element_name in self.g4_elements.keys():
            return self.g4_elements[element_name]
        # we build and store the G4 element if not
        if element_name in self.nist_element_names:
            be = self.g4_NistManager.FindOrBuildElement(element_name)
            self.g4_elements[element_name] = be
            return be
        if element_name not in self.element_builders:
            gate.fatal(f'Cannot find nor build element named "{element_name}"')
        be = self.element_builders[element_name].build()
        self.g4_elements[element_name] = be
        return be

    def get_database_material_names(self, db=None):
        if db is None:
            names = [m for m in self.material_builders]
            return names
        if db not in self.material_builders_by_filename:
            gate.fatal(
                f"The database '{db}' is not in the list of read database: {self.filenames}"
            )
        list = self.material_builders_by_filename[db]
        return [name for name in list]
