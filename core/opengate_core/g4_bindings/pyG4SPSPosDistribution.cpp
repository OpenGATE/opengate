/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4SPSPosDistribution.hh"
#include "G4SPSRandomGenerator.hh"

void init_G4SPSPosDistribution(py::module &m) {

    py::class_<G4SPSPosDistribution>(m, "G4SPSPosDistribution")
        .def(py::init())
        .def("GenerateOne", &G4SPSPosDistribution::GenerateOne)
        .def("SetPosDisType", &G4SPSPosDistribution::SetPosDisType)
        .def("SetPosDisShape", &G4SPSPosDistribution::SetPosDisShape)
        .def("SetCentreCoords", &G4SPSPosDistribution::SetCentreCoords)
        .def("SetPosRot1", &G4SPSPosDistribution::SetPosRot1)
        .def("SetPosRot2", &G4SPSPosDistribution::SetPosRot2)
        .def("SetHalfX", &G4SPSPosDistribution::SetHalfX)
        .def("SetHalfY", &G4SPSPosDistribution::SetHalfY)
        .def("SetHalfZ", &G4SPSPosDistribution::SetHalfZ)
        .def("SetRadius", &G4SPSPosDistribution::SetRadius)
        .def("SetRadius0", &G4SPSPosDistribution::SetRadius0)
        .def("SetBeamSigmaInR", &G4SPSPosDistribution::SetBeamSigmaInR)
        .def("SetBeamSigmaInX", &G4SPSPosDistribution::SetBeamSigmaInX)
        .def("SetBeamSigmaInY", &G4SPSPosDistribution::SetBeamSigmaInY)
        .def("SetParAlpha", &G4SPSPosDistribution::SetParAlpha)
        .def("SetParTheta", &G4SPSPosDistribution::SetParTheta)
        .def("SetParPhi", &G4SPSPosDistribution::SetParPhi)
        .def("SetBiasRndm", &G4SPSPosDistribution::SetBiasRndm)
        .def("ConfineSourceToVolume", &G4SPSPosDistribution::ConfineSourceToVolume)
        .def("SetVerbosity", &G4SPSPosDistribution::SetVerbosity);
}

