/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Version.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4DecayTable.hh"
#include "G4ProcessManager.hh"

void init_G4ParticleDefinition(py::module &m) {
    py::class_<G4ParticleDefinition>(m, "G4ParticleDefinition")

        .def("GetParticleName", &G4ParticleDefinition::GetParticleName,
             py::return_value_policy::reference)

        .def("GetPDGMass", &G4ParticleDefinition::GetPDGMass)
        .def("GetPDGWidth", &G4ParticleDefinition::GetPDGWidth)
        .def("GetPDGCharge", &G4ParticleDefinition::GetPDGCharge)
        .def("GetPDGSpin", &G4ParticleDefinition::GetPDGSpin)
        .def("GetPDGiSpin", &G4ParticleDefinition::GetPDGiSpin)
        .def("GetPDGiParity", &G4ParticleDefinition::GetPDGiParity)
        .def("GetPDGiConjugation", &G4ParticleDefinition::GetPDGiConjugation)
        .def("GetPDGIsospin", &G4ParticleDefinition::GetPDGIsospin)
        .def("GetPDGIsospin3", &G4ParticleDefinition::GetPDGIsospin3)
        .def("GetPDGiIsospin", &G4ParticleDefinition::GetPDGiIsospin)
        .def("GetPDGiIsospin3", &G4ParticleDefinition::GetPDGiIsospin3)
        .def("GetPDGiGParity", &G4ParticleDefinition::GetPDGiGParity)
        .def("GetParticleType", &G4ParticleDefinition::GetParticleType, py::return_value_policy::copy)
        .def("GetParticleSubType", &G4ParticleDefinition::GetParticleSubType, py::return_value_policy::copy)
        .def("GetLeptonNumber", &G4ParticleDefinition::GetLeptonNumber)
        .def("GetBaryonNumber", &G4ParticleDefinition::GetBaryonNumber)
        .def("GetPDGEncoding", &G4ParticleDefinition::GetPDGEncoding)
        .def("GetAntiPDGEncoding", &G4ParticleDefinition::GetAntiPDGEncoding)
        .def("GetQuarkContent", &G4ParticleDefinition::GetQuarkContent)
        .def("GetAntiQuarkContent", &G4ParticleDefinition::GetAntiQuarkContent)
        .def("IsShortLived", &G4ParticleDefinition::IsShortLived)
        .def("GetPDGStable", &G4ParticleDefinition::GetPDGStable)
        .def("SetPDGStable", &G4ParticleDefinition::SetPDGStable)
        .def("GetPDGLifeTime", &G4ParticleDefinition::GetPDGLifeTime)
        .def("SetPDGLifeTime", &G4ParticleDefinition::SetPDGLifeTime)
        .def("GetDecayTable", &G4ParticleDefinition::GetDecayTable, py::return_value_policy::reference_internal)
        .def("SetDecayTable", &G4ParticleDefinition::SetDecayTable)
        .def("GetProcessManager", &G4ParticleDefinition::GetProcessManager,
             py::return_value_policy::reference_internal)
        .def("SetProcessManager", &G4ParticleDefinition::SetProcessManager)

            // cludge!! (G4ParticleTable object is sigleton!!)
        .def("GetParticleTable", &G4ParticleDefinition::GetParticleTable, py::return_value_policy::reference)
        .def("DumpTable", &G4ParticleDefinition::DumpTable)
        .def("GetAtomicNumber", &G4ParticleDefinition::GetAtomicNumber)
        .def("GetAtomicMass", &G4ParticleDefinition::GetAtomicMass)
        .def("SetVerboseLevel", &G4ParticleDefinition::SetVerboseLevel)
        .def("GetVerboseLevel", &G4ParticleDefinition::GetVerboseLevel)
        .def("SetApplyCutsFlag", &G4ParticleDefinition::SetApplyCutsFlag)
        .def("GetApplyCutsFlag", &G4ParticleDefinition::GetApplyCutsFlag);
}
