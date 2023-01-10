import opengate as gate
import opengate_core as g4
import re
from box import Box


class MaterialBuilder:
    """
    A description of a material, that will can be build on demand.
    A material is described by a list of components that can be elements or sub-materials.
    """

    def __init__(self, material_database):
        self.type = "material"
        self.name = None
        self.symbol = None
        self.density = None
        self.n = None
        self.state = None
        self.components = {}
        self.material_database = material_database

    def __del__(self):
        pass

    def __repr__(self):
        s = f"({self.type}) {self.name} {self.density} {self.n} {self.components}"
        return s

    def read(self, f, line):
        # read the name
        s = line.split(":")
        if len(s) != 2:
            gate.fatal(
                f"Error line {line}, expecting a material name follow by a colon ':'."
            )
        name = s[0]
        self.name = name

        # reading density, n, state
        s = s[1].split(";")
        if len(s) != 3 and len(s) != 2:
            gate.fatal(f"Error while parsing material {self.name}, line {line}")

        # density
        self.density = gate.read_tag_with_unit(s[0], "d")
        if not self.density:
            gate.fatal(
                f"Error while parsing material {self.name}, line {line}\n"
                f'Expected density with "d=XXX"'
            )

        # nb of components
        self.n = int(gate.read_tag(s[1], "n"))

        # state
        if len(s) > 2:
            self.state = gate.read_tag(s[2], "state")
            if self.state:
                self.state = self.state.lower()

        # elements
        for e in range(self.n):
            line = gate.read_next_line(f)
            if line.startswith("+mat:"):
                e = self.read_one_submat(line)
                self.components[e.name] = e
            if line.startswith("+el"):
                e = self.read_one_element(line)
                self.components[e.name] = e

    def read_one_element(self, line):
        # skip the initial +el
        s = line.split("+el:")
        s = re.split("[;,]", s[1])
        if len(s) != 2:
            gate.fatal(
                f"Error while reading the line: {line} \n"
                f'Expected "name=" ; "n=" or "f="'
            )
        # read the name
        elname = gate.read_tag(s[0], "name")
        if elname == "auto":
            elname = self.name
        if not elname:
            gate.fatal(
                f"Error reading line {line} \n during the elements of material {self.name}"
            )
        # read f or n, put the other one to 'None'
        f = None
        n = gate.read_tag(s[1], "n")
        if not n:
            f = float(gate.read_tag(s[1], "f"))
        else:
            n = int(n)
        e = Box({"name": elname, "n": n, "f": f, "type": "element"})
        return e

    def read_one_submat(self, line):
        # skip the initial +mat
        s = line.split("+mat:")
        s = re.split("[;,]", s[1])
        if len(s) != 2:
            gate.fatal(
                f"Error while reading the line: {line} \n"
                f'Expected "name=" ; "n=" or "f="'
            )
        # read the name
        elname = gate.read_tag(s[0], "name")
        if not elname:
            gate.fatal(
                f"Error reading line {line} \n during the elements of material {self.name}"
            )
        # read f
        f = gate.read_tag(s[1], "f")
        if f is not None:
            f = float(f)
        else:
            gate.fatal(
                f"Error during reading material database {self.material_database.current_filename}"
                f", for the sub material {elname}, except fraction 'f=', while the line is {line}"
            )

        # build the dict
        e = Box({"name": elname, "n": None, "f": f, "type": "material"})
        return e

    def build(self):
        switcher = {
            None: g4.G4State.kStateUndefined,
            "solid": g4.G4State.kStateSolid,
            "liquid": g4.G4State.kStateLiquid,
            "gaz": g4.G4State.kStateGas,
            "gas": g4.G4State.kStateGas,
        }
        state = switcher.get(self.state, f"Invalid material state {self.state}")

        # default temp
        kelvin = gate.g4_units("kelvin")
        temp = 293.15 * kelvin

        # default pressure
        atmosphere = gate.g4_units("atmosphere")
        pressure = 1 * atmosphere

        # compute the correct nb of elements
        n = 0
        for elem in self.components.values():
            if elem.type == "element":
                n += 1
            else:
                subm = self.material_database.FindOrBuildMaterial(elem.name)
                n += len(subm.GetElementVector())

        # create material
        mat = g4.G4Material(self.name, self.density, n, state, temp, pressure)

        # add all components
        for elem in self.components.values():
            if elem.type == "element":
                self.add_element_to_material(mat, elem)
            else:
                self.add_submat_to_material(mat, elem)
        return mat

    def add_element_to_material(self, mat, elem):
        b = self.material_database.FindOrBuildElement(elem.name)
        if elem.f is None:
            mat.AddElementByNumberOfAtoms(b, elem.n)  # FIXME AddElementByMassFraction
        else:
            mat.AddElementByMassFraction(b, elem.f)

    def add_submat_to_material(self, mat, elem):
        subm = self.material_database.FindOrBuildMaterial(elem.name)
        elems = subm.GetElementVector()
        i = 0
        for el in elems:
            elf = subm.GetElementFraction(i)
            f = elf * elem.f
            name = str(el.GetName())
            b = self.material_database.FindOrBuildElement(name)
            mat.AddElementByMassFraction(b, f)
            i += 1
