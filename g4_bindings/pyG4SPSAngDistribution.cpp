/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4SPSAngDistribution.hh"
#include "G4SPSRandomGenerator.hh"

void init_G4SPSAngDistribution(py::module &m) {

    py::class_<G4SPSAngDistribution>(m, "G4SPSAngDistribution")
            .def(py::init())
            .def("GenerateOne", &G4SPSAngDistribution::GenerateOne)
            .def("SetAngDistType", &G4SPSAngDistribution::SetAngDistType)
            .def("DefineAngRefAxes", &G4SPSAngDistribution::DefineAngRefAxes)
            .def("SetMinTheta", &G4SPSAngDistribution::SetMinTheta)
            .def("SetMinPhi", &G4SPSAngDistribution::SetMinPhi)
            .def("SetMaxTheta", &G4SPSAngDistribution::SetMaxTheta)
            .def("SetMaxPhi", &G4SPSAngDistribution::SetMaxPhi)
            .def("SetBeamSigmaInAngR", &G4SPSAngDistribution::SetBeamSigmaInAngR)
            .def("SetBeamSigmaInAngX", &G4SPSAngDistribution::SetBeamSigmaInAngX)
            .def("SetBeamSigmaInAngY", &G4SPSAngDistribution::SetBeamSigmaInAngY)
            .def("UserDefAngTheta", &G4SPSAngDistribution::UserDefAngTheta)
            .def("UserDefAngPhi", &G4SPSAngDistribution::UserDefAngPhi)
            .def("SetFocusPoint", &G4SPSAngDistribution::SetFocusPoint)
            .def("SetParticleMomentumDirection", &G4SPSAngDistribution::SetParticleMomentumDirection)
            .def("SetUseUserAngAxis", &G4SPSAngDistribution::SetUseUserAngAxis)
            .def("SetUserWRTSurface", &G4SPSAngDistribution::SetUserWRTSurface)
            .def("SetPosDistribution", &G4SPSAngDistribution::SetPosDistribution)
            .def("SetBiasRndm", &G4SPSAngDistribution::SetBiasRndm)
            .def("ReSetHist", &G4SPSAngDistribution::ReSetHist)
            .def("SetVerbosity", &G4SPSAngDistribution::SetVerbosity);
}

