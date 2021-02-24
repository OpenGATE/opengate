/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4IonisParamMat.hh"

void init_G4IonisParamMat(py::module &m) {
    py::class_<G4IonisParamMat>(m, "G4IonisParamMat")
        .def("GetMeanExcitationEnergy", &G4IonisParamMat::GetMeanExcitationEnergy);
}

