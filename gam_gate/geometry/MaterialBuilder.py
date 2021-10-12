import gam_gate as gam
import gam_g4 as g4
import re
from box import Box


class MaterialBuilder:
    """
        Manage information (read from a file) to build a Geant4 material.
        Can be a G4Istope, G4Element or G4Material (a C-compound)
    """

    def __init__(self, material_database):
        self.type = 'element'
        self.name = None
        self.symbol = None
        self.Zeff = None
        self.Aeff = None
        self.density = None
        self.n = None
        self.state = None
        self.elements = {}
        self.material_database = material_database

    def __del__(self):
        pass

    def __repr__(self):
        u = gam.g4_units('g/mole')
        if self.type == 'element':
            s = f'({self.type}) {self.name} ({self.symbol}) Z={self.Zeff} A={self.Aeff / u} g/mole'
        else:
            s = f'({self.type}) {self.name} {self.n} {self.elements}'
        return s

    def read_tag(self, s, tag):
        w = s.split('=')
        if w[0].strip() != tag:
            return None
        value = w[1].strip()
        return value

    def read_tag_with_unit(self, s, tag):
        w = s.split('=')
        if w[0].strip() != tag:
            return None
        w = w[1].split()
        value = float(w[0])
        u = gam.g4_units(w[1].strip())
        return value * u

    def read_element(self, f, line):
        self.type = 'element'
        s = line.split(':')
        # name
        self.name = s[0]
        s = s[1].strip()
        s = s.split(';')
        # symbol
        self.symbol = self.read_tag(s[0], 'S')
        # Z
        self.Zeff = float(self.read_tag(s[1], 'Z'))
        # A with units
        self.Aeff = self.read_tag_with_unit(s[2], 'A')

    def read_material(self, f, line):
        self.type = 'material'
        s = line.split(':')
        # name
        name = s[0]
        if name == '+el':
            gam.fatal(f'Error line {line}, missing elements for the previous material ?')
        self.name = name
        s = s[1].split(';')
        if len(s) != 3 and len(s) != 2:
            gam.fatal(f'Error while parsing material {self.name}, line {line}')
        # density
        self.density = self.read_tag_with_unit(s[0], 'd')
        if not self.density:
            gam.fatal(f'Error while parsing material {self.name}, line {line}\n'
                      f'Expected density with "d=XXX"')
        # nb of elements
        self.n = int(self.read_tag(s[1], 'n'))
        # state
        if len(s) > 2:
            self.state = self.read_tag(s[2], 'state').lower()
        # elements
        elems = []
        for e in range(self.n):
            ee = self.read_one_element(f)
            elems.append(ee)
        # update the fraction
        total = 0
        n_is_used = elems[0].n
        for ee in elems:
            if ee.n and not n_is_used:
                gam.fatal(f'Error, some elements used "n" while other used "f", {self}')
            if n_is_used:
                total += ee.n
            else:
                total += ee.f
        for ee in elems:
            if n_is_used:
                ee.f = ee.n / total

    def read_one_element(self, f):
        line = f.readline().strip()
        if line[:4] != '+el:':
            gam.fatal(f'Error, expect "+el:" at the beginning of this line: {line}\n'
                      f' while parsing the material {self.name}')
            return
        s = line.split('+el:')
        s = re.split(';|,', s[1])
        if len(s) != 2:
            gam.fatal(f'Error while reading the line: {line} \n'
                      f'Expected "name=" ; "n=" or "f="')
        elname = self.read_tag(s[0], 'name')
        if elname == 'auto':
            elname = self.name
        if not elname:
            gam.fatal(f'Error reading line {line} \n during the elements of material {self.name}')
        n = None
        f = None
        n = self.read_tag(s[1], 'n')
        if not n:
            f = float(self.read_tag(s[1], 'f'))
        else:
            n = float(n)
        e = Box({'name': elname, 'n': n, 'f': f})
        self.elements[elname] = e
        return e

    def build(self):
        if self.type == 'element':
            return self.build_element()
        if self.type == 'isotope':
            return self.build_isotope()
        if self.type == 'material':
            return self.build_material()
        gam.fatal(f'Error, material type unknown: {self.type}')

    def build_isotope(self):
        print('build_isotope')
        gam.fatal(f'Not yet implemented')
        # FIXME LATER

    def build_element(self):
        m = g4.G4Element(self.name, self.symbol, self.Zeff, self.Aeff)
        # FIXME alternative with Build an element from isotopes via AddIsotope ?
        return m

    def build_material(self):
        n = len(self.elements)
        switcher = {None: g4.G4State.kStateUndefined,
                    'solid': g4.G4State.kStateSolid,
                    'liquid': g4.G4State.kStateLiquid,
                    'gaz': g4.G4State.kStateGas}
        state = switcher.get(self.state, f'Invalid material state {self.state}')
        # default temp
        kelvin = gam.g4_units('kelvin')
        temp = 293.15 * kelvin
        # default pressure
        atmosphere = gam.g4_units('atmosphere')
        pressure = 1 * atmosphere
        # create material
        m = g4.G4Material(self.name, self.density, n, state, temp, pressure)
        # warning: cannot print while all elements are not added
        for elem in self.elements:
            b = self.material_database.FindOrBuildElement(elem)
            m.AddElement(b, self.elements[elem].f)
        return m
