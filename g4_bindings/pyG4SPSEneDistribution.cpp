/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4SPSEneDistribution.hh"

void init_G4SPSEneDistribution(py::module &m) {

    py::class_<G4SPSEneDistribution>(m, "G4SPSEneDistribution")
            .def(py::init())
            .def("GenerateOne", &G4SPSEneDistribution::GenerateOne)
            .def("SetEnergyDisType", &G4SPSEneDistribution::SetEnergyDisType)
            .def("SetEmin", &G4SPSEneDistribution::SetEmin)
            .def("SetEmax", &G4SPSEneDistribution::SetEmax)
            .def("SetMonoEnergy", &G4SPSEneDistribution::SetMonoEnergy)
            .def("SetAlpha", &G4SPSEneDistribution::SetAlpha)
            .def("SetBiasAlpha", &G4SPSEneDistribution::SetBiasAlpha)
            .def("SetTemp", &G4SPSEneDistribution::SetTemp)
            .def("SetBeamSigmaInE", &G4SPSEneDistribution::SetBeamSigmaInE)
            .def("SetEzero", &G4SPSEneDistribution::SetEzero)
            .def("SetGradient", &G4SPSEneDistribution::SetGradient)
            .def("SetInterCept", &G4SPSEneDistribution::SetInterCept)
            .def("UserEnergyHisto", &G4SPSEneDistribution::UserEnergyHisto)
            .def("ArbEnergyHisto", &G4SPSEneDistribution::ArbEnergyHisto)
            .def("ArbEnergyHistoFile", &G4SPSEneDistribution::ArbEnergyHistoFile)
            .def("EpnEnergyHisto", &G4SPSEneDistribution::EpnEnergyHisto)
            .def("InputEnergySpectra", &G4SPSEneDistribution::InputEnergySpectra)
            .def("InputDifferentialSpectra", &G4SPSEneDistribution::InputDifferentialSpectra)
            .def("ArbInterpolate", &G4SPSEneDistribution::ArbInterpolate)
            .def("SetVerbosity", &G4SPSEneDistribution::SetVerbosity);
}

