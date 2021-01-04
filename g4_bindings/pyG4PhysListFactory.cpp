/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>

namespace py = pybind11;

#include "G4PhysListFactory.hh"
#include "G4VModularPhysicsList.hh"

void init_G4PhysListFactory(py::module &m) {

    py::class_<G4PhysListFactory,
            std::unique_ptr<G4PhysListFactory, py::nodelete>>(m, "G4PhysListFactory")
            .def(py::init())
            .def("AvailablePhysLists", &G4PhysListFactory::AvailablePhysLists)
            .def("GetReferencePhysList", &G4PhysListFactory::GetReferencePhysList, py::return_value_policy::reference);
}

