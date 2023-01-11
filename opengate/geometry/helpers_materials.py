import opengate as gate
import os
import numpy as np
import opengate_core as g4


def read_voxel_materials(filename, def_mat="G4_AIR"):
    p = os.path.abspath(filename)
    f = open(p, "r")
    current = 0
    materials = []
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
            gate.fatal(
                f"Error while reading {filename}\n"
                f"Intervals are not disjoint: {previous} {m}"
            )
        if m[0] > m[1]:
            gate.fatal(f"Error while reading {filename}\n" f"Wrong interval {m}")
        if not previous or previous == m[0]:
            pix_mat.append([previous, m[1], m[2]])
            previous = m[1]
        else:
            pix_mat.append([previous, m[0], def_mat])
            pix_mat.append([previous, m[1], m[2]])
            previous = m[1]

    return pix_mat


def new_material_weights(name, density, elements, weights=[1]):
    n = g4.G4NistManager.Instance()
    if not isinstance(elements, list):
        elements = [elements]
    if len(elements) != len(weights):
        gate.fatal(
            f"Cannot create the new material, the elements and the "
            f"weights does not have the same size: {elements} and {weights}"
        )
    total = np.sum(weights)
    weights = weights / total
    m = n.ConstructNewMaterialWeights(name, elements, weights, density)
    return m


def new_material_nb_atoms(name, density, elements, nb_atoms):
    n = g4.G4NistManager.Instance()
    if not isinstance(elements, list):
        elements = [elements]
    if len(elements) != len(nb_atoms):
        gate.fatal(
            f"Cannot create the new material, the elements and the "
            f"nb_atoms does not have the same size: {elements} and {nb_atoms}"
        )
    nb_atoms = [int(x) for x in nb_atoms]
    m = n.ConstructNewMaterialNbAtoms(name, elements, nb_atoms, density)
    return m


def HU_read_materials_table(file_mat):
    p = os.path.abspath(file_mat)
    f = open(p, "r")
    elements = ["HU"]
    materials = []
    current_section = None
    current_material = None
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
    f = open(p, "r")
    densities = []
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


# correspondence element names <> symbol
elements_name_symbol = {
    "Hydrogen": "H",
    "Carbon": "C",
    "Nitrogen": "N",
    "Oxygen": "O",
    "Sodium": "Na",
    "Magnesium": "Mg",
    "Phosphor": "P",
    "Sulfur": "S",
    "Chlorine": "Cl",
    "Argon": "Ar",
    "Potassium": "K",
    "Calcium": "Ca",
    "Titanium": "Ti",
    "Copper": "Cu",
    "Zinc": "Zn",
    "Silver": "Ag",
    "Tin": "Sn",
}


def HounsfieldUnit_to_material(density_tolerance, file_mat, file_density):
    """
    Same function than in GateHounsfieldToMaterialsBuilder class.
    Probably far from optimal, put we keep the compatibility
    """

    materials, elements = HU_read_materials_table(file_mat)
    densities = HU_read_density_table(file_density)
    voxel_materials = []
    created_materials = []
    gcm3 = gate.g4_units("g/cm3")

    elems = elements[1 : len(elements) - 1]
    elems_symbol = [elements_name_symbol[x] for x in elems]

    i = 0
    num = 0
    last_i = len(materials) - 1
    nm = g4.G4NistManager.Instance()
    for mat in materials:
        # get HU interval
        hu_min = mat["HU"]
        if i == last_i:
            hu_max = hu_min + 1
        else:
            hu_max = materials[i + 1]["HU"]

        # check hu min max
        if hu_max <= hu_min:
            gate.fatal(f"Error, HU interval not valid: {mat}")

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
            # create a new material
            m = nm.ConstructNewMaterialWeights(
                f'{mat["name"]}_{num}', elems_symbol_nz, weights_nz, d * gcm3
            )
            # get the final correspondence
            c = [h1, h2, str(m.GetName())]
            voxel_materials.append(c)
            created_materials.append(m)
            num = num + 1
        #
        i = i + 1
    return voxel_materials, created_materials


def dump_material_like_Gate(mat):
    s = f'{mat.GetName()}: d={gate.g4_best_unit(mat.GetDensity(), "Volumic Mass")}; n={mat.GetNumberOfElements()}\n'
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
    u = gate.g4_units(w[1].strip())
    return value * u
