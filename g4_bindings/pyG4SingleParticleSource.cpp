/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4SingleParticleSource.hh"
#include "G4Event.hh"

void init_G4SingleParticleSource(py::module &m) {

    py::class_<G4SingleParticleSource>(m, "G4SingleParticleSource")
        .def(py::init())
        .def("GeneratePrimaryVertex", &G4SingleParticleSource::GeneratePrimaryVertex)
        .def("SetParticleDefinition", &G4SingleParticleSource::SetParticleDefinition)
        .def("SetParticleCharge", &G4SingleParticleSource::SetParticleCharge)
        .def("SetParticlePolarization", &G4SingleParticleSource::SetParticlePolarization)
        .def("SetParticleTime", &G4SingleParticleSource::SetParticleTime)
        .def("SetNumberOfParticles", &G4SingleParticleSource::SetNumberOfParticles)
        .def("GetPosDist", &G4SingleParticleSource::GetPosDist, py::return_value_policy::reference)
        .def("GetAngDist", &G4SingleParticleSource::GetAngDist, py::return_value_policy::reference)
        .def("GetEneDist", &G4SingleParticleSource::GetEneDist, py::return_value_policy::reference)
        .def("SetVerbosity", &G4SingleParticleSource::SetVerbosity);
}

