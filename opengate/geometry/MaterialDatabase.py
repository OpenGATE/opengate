from .MaterialBuilder import *
from .ElementBuilder import *


class MaterialDatabase:
    """
    Manage a unique list of Geant4 materials and elements.
    """

    def __init__(self):
        self.filenames = []
        self.material_builders = {}
        self.element_builders = {}
        self.g4_materials = {}
        self.g4_elements = {}
        # internal state
        self.current_section = None
        self.current_filename = None
        self.g4_NistManager = None
        self.nist_material_names = None
        self.nist_element_names = None

    def __del__(self):
        pass

    def read_builders_from_file(self, filename):
        self.filenames.append(filename)
        self.current_filename = filename
        f = open(filename, "r")
        line = f.readline()
        while line:
            line = line.strip().replace("\t", " ")
            self.read_one_item(f, line)
            line = f.readline()
        print("end read", self.material_builders)

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
        if self.current_section == "material":
            b = MaterialBuilder(self)
            b.read(f, line)
            self.material_builders[b.name] = b

    def init_NIST(self):
        if self.g4_NistManager is None:
            self.g4_NistManager = g4.G4NistManager.Instance()
            self.nist_element_names = self.g4_NistManager.GetNistElementNames()
            self.nist_material_names = self.g4_NistManager.GetNistMaterialNames()
            print(self.material_builders)

    def FindOrBuildMaterial(self, material):
        print("FindOrBuildMaterial", material)
        self.init_NIST()
        # return if already exist
        if material in self.g4_materials:
            return self.g4_materials[material]
        # we build and store the G4 material if not
        if material in self.nist_material_names:
            print("NIST")
            bm = self.g4_NistManager.FindOrBuildMaterial(material)
            self.g4_materials[material] = bm
            return bm
        if material not in self.material_builders:
            gate.fatal(f'Cannot find nor build material named "{material}"')
        bm = self.material_builders[material].build()
        self.g4_materials[material] = bm
        return bm

    def FindOrBuildElement(self, element):
        self.init_NIST()
        # return if already exist
        if element in self.g4_elements:
            return self.g4_elements[element]
        # we build and store the G4 element if not
        if element in self.nist_material_names:
            bm = self.g4_NistManager.FindOrBuildElement(element)
            return bm
        if element not in self.element_builders:
            gate.fatal(f'Cannot find nor build element named "{element}"')
        be = self.element_builders[element].build()
        self.g4_elements[element] = be
        return be
