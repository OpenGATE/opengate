/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Step.hh"

void init_G4Step(py::module &m) {

    py::class_<G4Step>(m, "G4Step")
        .def(py::init())
        .def("GetTotalEnergyDeposit", &G4Step::GetTotalEnergyDeposit)
        .def("GetPreStepPoint", &G4Step::GetPreStepPoint, py::return_value_policy::reference)
        .def("GetPostStepPoint", &G4Step::GetPostStepPoint, py::return_value_policy::reference)
        .def("GetTrack", &G4Step::GetTrack, py::return_value_policy::reference)

        /*
         * TODO
         GetDeltaPosition GetDeltaTime
         GetDeltaMomentum GetDeltaEnergy
         GetNumberOfSecondariesInCurrentStep
         GetSecondaryInCurrentStep -> Track

         */

        ;
}

