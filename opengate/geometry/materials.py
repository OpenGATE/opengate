import os
import numpy as np
import re
from box import Box
import itk

import opengate_core as g4
from ..utility import fatal, g4_units, g4_best_unit
from ..definitions import elements_name_symbol


def read_voxel_materials(filename, def_mat="G4_AIR"):
    p = os.path.abspath(filename)
    current = 0
    materials = []
    with open(p, "r") as f:
        for line in f:
            for word in line.split():
                if word[0] == "#":
                    break
                if current == 0:
                    start = float(word)
                    current = 1
                else:
                    if current == 1:
                        stop = float(word)
                        current = 2
                    else:
                        if current == 2:
                            mat = word
                            current = 0
                            materials.append([start, stop, mat])

    # sort according to starting interval
    materials = sorted(materials)

    # consider all values
    pix_mat = []
    previous = None
    for m in materials:
        if previous and previous > m[0]:
            fatal(
                f"Error while reading {filename}\n"
                f"Intervals are not disjoint: {previous} {m}"
            )
        if m[0] > m[1]:
            fatal(f"Error while reading {filename}\n" f"Wrong interval {m}")
        if not previous or previous == m[0]:
            pix_mat.append([previous, m[1], m[2]])
            previous = m[1]
        else:
            pix_mat.append([previous, m[0], def_mat])
            pix_mat.append([previous, m[1], m[2]])
            previous = m[1]

    return pix_mat


def HU_read_materials_table(file_mat):
    p = os.path.abspath(file_mat)
    elements = ["HU"]
    materials = []
    current_section = None
    current_material = None
    with open(p, "r") as f:
        for line in f:
            i = 0
            for word in line.split():
                if word[0] == "#":
                    break
                if word == "[Elements]":
                    current_section = "element"
                    break
                if word == "[/Elements]":
                    elements.append("name")
                    current_section = "table"
                    break
                if current_section is None:
                    break
                if current_section == "element":
                    elements.append(word)
                if current_section == "table":
                    if current_material is None:
                        current_material = {}
                    if i == 0:
                        current_material[elements[i]] = int(word)
                    else:
                        if i == len(elements) - 1:
                            current_material[elements[i]] = word
                        else:
                            current_material[elements[i]] = float(word)
                i += 1
            if current_material:
                materials.append(current_material)
            current_material = None
    return materials, elements


def HU_read_density_table(file_density):
    p = os.path.abspath(file_density)
    densities = []
    with open(p, "r") as f:
        for line in f:
            words = line.split()
            if len(words) < 1:
                continue
            if words[0][0] == "#":
                continue
            d = {"HU": int(words[0]), "density": float(words[1])}
            densities.append(d)
    return densities


def HU_linear_interpolate_densities(hu, densities):
    i = 0
    n = len(densities)
    while i < n and hu > densities[i]["HU"]:
        i = i + 1
    i = i - 1
    if i < 0:
        return densities[0]["density"]
    if i >= n - 1:
        return densities[n - 1]["density"]
    v = ((hu - densities[i]["HU"]) / (densities[i + 1]["HU"] - densities[i]["HU"])) * (
        densities[i + 1]["density"] - densities[i]["density"]
    ) + densities[i]["density"]
    return v


def HU_find_max_density_difference(hu_min, hu_max, d_min, d_max, densities):
    n = len(densities)
    i = 0
    while i < n and hu_min > densities[i]["HU"]:
        i = i + 1
    j = 0
    while j < n and hu_max > densities[j]["HU"]:
        j = j + 1
    j = j - 1
    for x in range(i, j, 1):
        if densities[i]["density"] < d_min:
            d_min = densities[i]["density"]
        if densities[i]["density"] > d_max:
            d_max = densities[i]["density"]
    return d_max - d_min


def HounsfieldUnit_to_material(simulation, density_tolerance, file_mat, file_density):
    """
    Same function than in GateHounsfieldToMaterialsBuilder class.
    Probably far from optimal, put we keep the compatibility
    """

    materials, elements = HU_read_materials_table(file_mat)
    densities = HU_read_density_table(file_density)
    voxel_materials = []
    created_materials = []
    gcm3 = g4_units.g_cm3

    elems = elements[1 : len(elements) - 1]
    elems_symbol = [elements_name_symbol[x] for x in elems]

    i = 0
    num = 0
    last_i = len(materials) - 1
    for mat in materials:
        # get HU interval
        hu_min = mat["HU"]
        if i == last_i:
            hu_max = hu_min + 1
        else:
            hu_max = materials[i + 1]["HU"]

        # check hu min max
        if hu_max <= hu_min:
            fatal(f"Error, HU interval not valid: {mat}")

        # get densities interval
        dmin = HU_linear_interpolate_densities(hu_min, densities)
        dmax = HU_linear_interpolate_densities(hu_max, densities)
        ddiff = HU_find_max_density_difference(hu_min, hu_max, dmin, dmax, densities)

        # nb of bins
        n = max(1, ddiff * gcm3 / density_tolerance)
        # n_naive = max(1, (dmax - dmin) * gcm3 / density_tolerance)

        # check if AIR
        if "Air" in mat["name"] or "AIR" in mat["name"]:
            n = 1

        # HU interval according to tolerance
        htol = (hu_max - hu_min) / n

        # like in Gate
        if n != 1:
            n = int(np.ceil(n))

        # loop on density interval
        for j in range(n):
            h1 = hu_min + j * htol
            h2 = min(hu_min + (j + 1) * htol, hu_max)
            d = HU_linear_interpolate_densities(h1 + (h2 - h1) / 2.0, densities)
            # create a new material with the interpolated density
            weights = [mat[x] for x in elems]
            weights_nz = []
            elems_symbol_nz = []
            # remove the weight equal to zero
            sum = 0
            for a, e in zip(weights, elems_symbol):
                if a > 0:
                    weights_nz.append(a)
                    elems_symbol_nz.append(e)
                    sum += a
            # normalise weight
            for k in range(len(weights_nz)):
                weights_nz[k] = weights_nz[k] / sum
            # define a new material (will be created later at MaterialDatabase initialize)
            name = f'{mat["name"]}_{num}'
            simulation.volume_manager.material_database.add_material_weights(
                name, elems_symbol_nz, weights_nz, d * gcm3
            )
            # get the final correspondence
            c = [h1, h2, name]
            voxel_materials.append(c)
            created_materials.append(name)
            num = num + 1
        #
        i = i + 1
    return voxel_materials, created_materials


def dump_material_like_Gate(mat):
    s = f'{mat.GetName()}: d={g4_best_unit(mat.GetDensity(), "Volumic Mass")}; n={mat.GetNumberOfElements()}\n'
    i = 0
    for elem in mat.GetElementVector():
        s += f"+el: name={elem.GetName()}; f={mat.GetElementFraction(i)}\n"
        i += 1
    s += "\n"
    return s


def assert_same_material(m1, m2):
    if m1.name != m2.name:
        return False
    if np.fabs(m1.density - m2.density) / m1.density > 1e-2:
        print("Error while comparing materials", m1, m2)
        print(np.fabs(m1.density - m2.density) / m1.density)
        print(m1)
        print(m2)
        return False
    for e1 in m1.components:
        e2 = m2.components[elements_name_symbol[e1]]
        e1 = m1.components[e1]
        if elements_name_symbol[e1.name] != e2.name:
            print("Error while comparing materials", m1, m2)
            print(e1, e2)
            return False
        if e1.n != e2.n:
            print("Error while comparing materials", m1, m2)
            print(e1, e2)
            return False
        if np.fabs(e1.f - e2.f) / e1.f > 1e-2:
            print("Error while comparing materials", m1, m2)
            print(e1, e2)
            return False

    return True


def read_next_line(f):
    line = f.readline()
    return line.strip().replace("\t", " ")


def read_tag(s, tag):
    w = s.split("=")
    if w[0].strip() != tag:
        return None
    value = w[1].strip()
    return value


def read_tag_with_unit(s, tag):
    w = s.split("=")
    if w[0].strip() != tag:
        return None
    w = w[1].split()
    value = float(w[0])
    u = g4_units[w[1].strip()]
    return value * u


def create_density_img(img_volume, material_database):
    """


    Parameters
    ----------
    img_volume : ImageVolume
        opengate ImageVolume class instance
    material_database : dict
        dictionary with keys: material name, values: G4 material obj

    Returns
    -------
    rho : itk.Image
        image of the same size and resolution of the ct. The voxel value is the density of the voxel.
        Density is returned in G4 1/kg.

    """
    voxel_materials = img_volume.voxel_materials
    ct_itk = img_volume.itk_image
    act = itk.GetArrayFromImage(ct_itk)
    arho = np.zeros(act.shape, dtype=np.float32)

    for material in voxel_materials:
        *hu_interval, mat_name = material
        hu0, hu1 = hu_interval
        m = (act >= hu0) * (act < hu1)
        density = material_database[mat_name].GetDensity()
        arho[m] = density

    rho = itk.GetImageFromArray(arho)
    rho.CopyInformation(ct_itk)

    return rho


def create_mass_img(ct_itk, hu_density_file, overrides=dict()):
    """


    Parameters
    ----------
    ct_itk :itk.Image
        ct image
    hu_density_file : str
        filepath of the HU to density table
    overrides : dict, optional
        Dict where keys are HU to be overwritten and values
        are density values. The default is dict().

    Returns
    -------
    mass : itk.Image
        image of the same size and resolution of the ct. The voxel value is the mass of the voxel.
        Mass is returned in grams.

    """
    hlut = HU_read_density_table(hu_density_file)
    act = itk.GetArrayFromImage(ct_itk)
    amass = np.zeros(act.shape, dtype=np.float32)
    done = np.zeros(act.shape, dtype=bool)

    m = act < hlut[0]["HU"]
    amass[m] = hlut[0]["density"]
    done |= m
    m = act >= hlut[-1]["HU"]
    amass[m] = hlut[-1]["density"]
    done |= m

    # interpolate for intermediate values
    for hlut0, hlut1 in zip(hlut[:-1], hlut[1:]):
        hu0, rho0 = hlut0["HU"], hlut0["density"]
        hu1, rho1 = hlut1["HU"], hlut1["density"]
        m = (act >= hu0) * (act < hu1)
        assert not (m * done).any(), "programming error"
        amass[m] = rho0
        amass[m] += (act[m] - hu0) * (rho1 - rho0) / (hu1 - hu0)
        done |= m
    assert done.all(), "programming error"

    #  override density for specific HU values
    for hu, rho in overrides.items():
        assert hu == int(hu), "overrides must be given for integer HU values"
        assert rho >= 0, "override density values must be non-negative"
        m = act == hu
        amass[m] = rho
        done |= m

    spacing = ct_itk.GetSpacing()
    voxel_vol = (
        spacing[0] * spacing[1] * spacing[2] * 1e-3
    )  # density in g/cm3 -> spacing in mm
    amass *= voxel_vol  # mass in g

    mass = itk.GetImageFromArray(amass)
    mass.CopyInformation(ct_itk)

    return mass


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

    def __repr__(self):
        u = g4_units.g_mole
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


class MaterialBuilder:
    """
    A description of a material, that will can be built on demand.
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

    def __repr__(self):
        s = f"({self.type}) {self.name} {self.density} {self.n} {self.components}"
        return s

    def read(self, f, line):
        # read the name
        s = line.split(":")
        if len(s) != 2:
            fatal(
                f"Error line {line}, expecting a material name follow by a colon ':'."
            )
        name = s[0]
        self.name = name

        # reading density, n, state
        s = s[1].split(";")
        if len(s) != 3 and len(s) != 2:
            fatal(f"Error while parsing material {self.name}, line {line}")

        # density
        self.density = read_tag_with_unit(s[0], "d")
        if not self.density:
            fatal(
                f"Error while parsing material {self.name}, line {line}\n"
                f'Expected density with "d=XXX"'
            )

        # nb of components
        self.n = int(read_tag(s[1], "n"))

        # state
        if len(s) > 2:
            self.state = read_tag(s[2], "state")
            if self.state:
                self.state = self.state.lower()

        # elements
        for e in range(self.n):
            line = read_next_line(f)
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
            fatal(
                f"Error while reading the line: {line} \n"
                f'Expected "name=" ; "n=" or "f="'
            )
        # read the name
        elname = read_tag(s[0], "name")
        if elname == "auto":
            elname = self.name
        if not elname:
            fatal(
                f"Error reading line {line} \n during the elements of material {self.name}"
            )
        # read f or n, put the other one to 'None'
        f = None
        n = read_tag(s[1], "n")
        if not n:
            f = float(read_tag(s[1], "f"))
        else:
            n = int(n)
        e = Box({"name": elname, "n": n, "f": f, "type": "element"})
        return e

    def read_one_submat(self, line):
        # skip the initial +mat
        s = line.split("+mat:")
        s = re.split("[;,]", s[1])
        if len(s) != 2:
            fatal(
                f"Error while reading the line: {line} \n"
                f'Expected "name=" ; "n=" or "f="'
            )
        # read the name
        elname = read_tag(s[0], "name")
        if not elname:
            fatal(
                f"Error reading line {line} \n during the elements of material {self.name}"
            )
        # read f
        f = read_tag(s[1], "f")
        if f is not None:
            f = float(f)
        else:
            fatal(
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
        kelvin = g4_units.kelvin
        temp = 293.15 * kelvin

        # default pressure
        atmosphere = g4_units.atmosphere
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
        # additional manually added materials
        self.new_materials_nb_atoms = {}
        self.new_materials_weights = {}
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

    def __getstate__(self):
        return_dict = self.__dict__
        # remove items that cannot be pickled, e.g. G4 objects
        return_dict["g4_materials"] = {}
        return_dict["g4_elements"] = {}
        return_dict["g4_NistManager"] = None
        return_dict["nist_material_names"] = None
        return_dict["nist_element_names"] = None
        return_dict["material_builders_by_filename"].pop("NIST", None)
        return_dict["element_builders_by_filename"].pop("NIST", None)
        return return_dict

    def __setstate__(self, state):
        self.__dict__ = state
        self.initialize()

    def read_from_file(self, filename):
        self.filenames.append(filename)
        self.current_filename = filename
        self.element_builders_by_filename[self.current_filename] = {}
        self.material_builders_by_filename[self.current_filename] = {}
        with open(filename, "r") as f:
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
            fatal(
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

    # FIXME: make arguments explicit
    def add_material_nb_atoms(self, *args):
        """
        Usage example:
        "Lead", ["Pb"], [1], 11.4 * gcm3
        "BGO", ["Bi", "Ge", "O"], [4, 3, 12], 7.13 * gcm3)
        """
        name = args[0]
        self.new_materials_nb_atoms[name] = args

    # FIXME: make arguments explicit
    def add_material_weights(self, *args):
        """
        Usage example :
        add_material_weights(name, elems_symbol_nz, weights_nz, 3 * gcm3)
        """
        name = args[0]
        self.new_materials_weights[name] = args

    def initialize(self):
        self.init_NIST()
        self.init_user_mat()

    def init_user_mat(self):
        for mat_name in self.new_materials_nb_atoms:
            if mat_name in self.g4_materials:
                fatal(f"Material {mat_name} is already constructed")
            mat_info = self.new_materials_nb_atoms[mat_name]
            try:
                mat = self.g4_NistManager.ConstructNewMaterialNbAtoms(*mat_info)
            except:  # FIXME: this should specify the exception to catch
                fatal(f"Cannot construct the material (nb atoms): {mat_info}")
            self.g4_materials[mat_name] = mat
        self.new_materials_nb_atoms = []
        for mat_name in self.new_materials_weights:
            if mat_name in self.g4_materials:
                fatal(f"Material {mat_name} is already constructed")
            mat_info = self.new_materials_weights[mat_name]
            try:
                mat = self.g4_NistManager.ConstructNewMaterialWeights(*mat_info)
            except:
                fatal(f"Cannot construct the material (weights): {mat_info}")
            self.g4_materials[mat_name] = mat
        self.new_materials_weights = []

    def FindOrBuildMaterial(self, material_name):
        self.init_NIST()
        self.init_user_mat()
        # try to build the material if it does not yet exist
        if material_name not in self.g4_materials:
            if material_name in self.nist_material_names:
                self.g4_materials[material_name] = (
                    self.g4_NistManager.FindOrBuildMaterial(material_name)
                )
            elif material_name in self.material_builders:
                self.g4_materials[material_name] = self.material_builders[
                    material_name
                ].build()
            else:
                fatal(f'Cannot find nor build material named "{material_name}"')
        return self.g4_materials[material_name]

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
            fatal(f'Cannot find nor build element named "{element_name}"')
        be = self.element_builders[element_name].build()
        self.g4_elements[element_name] = be
        return be

    def get_database_material_names(self, db=None):
        if db is None:
            names = [m for m in self.material_builders]
            return names
        if db not in self.material_builders_by_filename:
            fatal(
                f"The database '{db}' is not in the list of read database: {self.filenames}"
            )
        list = self.material_builders_by_filename[db]
        return [name for name in list]
