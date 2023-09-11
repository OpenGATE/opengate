import opengate_core as g4
from ..helpers import g4_units
from .helpers_materials import read_tag, read_tag_with_unit


class ElementBuilder:
    """
    A description of a G4Element that can be build.
    """

    def __init__(self, material_database):
        self.type = "element"
        self.name = None
        self.symbol = None
        self.Zeff = None
        self.Aeff = None
        self.material_database = material_database

    def __del__(self):
        pass

    def __repr__(self):
        u = g4_units("g/mole")
        s = f"({self.type}) {self.name} ({self.symbol}) Z={self.Zeff} A={self.Aeff / u} g/mole"
        return s

    def read(self, line):
        self.type = "element"
        s = line.split(":")
        # name
        self.name = s[0]
        s = s[1].strip()
        s = s.split(";")
        # symbol
        self.symbol = read_tag(s[0], "S")
        # Z
        self.Zeff = float(read_tag(s[1], "Z"))
        # A with units
        self.Aeff = read_tag_with_unit(s[2], "A")

    def build(self):
        m = g4.G4Element(self.name, self.symbol, self.Zeff, self.Aeff)
        # FIXME alternative with Build an element from isotopes via AddIsotope ?
        return m
