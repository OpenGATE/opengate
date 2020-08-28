/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamTestProtonSource.h"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4Event.hh"

void init_GamTestProtonSource(py::module &m) {

    py::class_<GamTestProtonSource, G4VUserPrimaryGeneratorAction>(m, "GamTestProtonSource")
        .def(py::init())
        .def("GeneratePrimaries", &GamTestProtonSource::GeneratePrimaries);
}

