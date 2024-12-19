# -*- coding: utf-8 -*-
"""
Created on Thu Jun 25 11:52:20 2015
Function providing the mass attenuation coefficient, the mass energy absorption coefficient
and the linear attenuation coefficient of a mixture for energies in [0.001,20] MeV range.
@author: vilches
"""

from .PhotonAttenuation import *


def PhotonAttenuationMixture(Mixture, E, Option):
    [w, El] = ChComposition(
        Mixture
    )  # extract fraction by weight and elements of the mixture
    d = PropsMix[
        PropsMix[:, 2] == Mixture, 1
    ]  # extract the density of the mixture from PropsMix
    Z = [0 for i in range(len(El))]
    for i in range(0, len(El)):
        Z[i] = np.where(PropsEl[:, 2] == El[i])
    ix = [x[0] for x in Z]
    idx = list(map(int, ix))  # assign atomic number value to each element
    w = list(map(float, np.asarray(w)))
    d = list(map(float, d))
    murho = [0 for j in range(len(idx))]
    murhoMix = [0 for j in range(len(idx))]
    muMix = [0 for j in range(len(idx))]
    muMixture = [0 for k in range(len(idx))]

    if Option == 1:  # mass attenuation coefficient of the mixture
        for i in range(0, len(idx)):
            murho[i] = PhotonAttenuationEl((idx[i] + 1), E, 1)  # mac
            murhoMix[i] = np.dot(murho[i], w[i])
        muMix = np.multiply(np.asarray(murhoMix), 1)
        muMixture = muMix.sum(axis=0)

    elif Option == 2:  # mass energy absorption coefficient of the mixture
        for i in range(0, len(idx)):
            murho[i] = PhotonAttenuationEl((idx[i] + 1), E, 2)  # meac
            murhoMix[i] = np.dot(murho[i], w[i])
        muMix = np.multiply(np.asarray(murhoMix), 1)
        muMixture = muMix.sum(axis=0)

    elif Option == 3:  # linear attenuation coefficient of the mixture
        for i in range(0, len(idx)):
            murho[i] = PhotonAttenuationEl((idx[i] + 1), E, 1)  # mac
            murhoMix[i] = np.dot(murho[i], w[i])
        muMix = np.multiply(np.asarray(murhoMix), d)  # from mac to lac
        muMixture = muMix.sum(axis=0)
    elif Option > 3:
        print("Error! Only three outputs are possible!")
        return ["Set the function inputs again"]
    return muMixture


# Example 1:
# E = 0.001
# result = PhotonAttenuationMixture('Soft Tissue', E, 3)
# print result

## Example 2:
# E = np.arange(0.001,0.01,0.001) # CT imaging range: from 1 keV to 150 keV
# result = [ 0 for i in range(len(E))]
# for i in range(0,len(E)):
#    result = PhotonAttenuationMixture('Air', E, 2)
# print result
