import sys
import numpy as np

# This files contains definitions of common variables used throughout opengate

""" Global name for the world volume"""
__world_name__ = "world"


FLOAT_MAX = sys.float_info.max

sigma_to_fwhm = 2 * np.sqrt(2 * np.log(2))
fwhm_to_sigma = 1.0 / sigma_to_fwhm

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
