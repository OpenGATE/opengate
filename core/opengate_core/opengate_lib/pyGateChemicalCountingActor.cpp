/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateChemicalCountingActor.h"

void init_GateChemicalCountingActor(py::module &m) {
  py::class_<GateChemicalCountingActor,
             std::unique_ptr<GateChemicalCountingActor, py::nodelete>,
             GateVChemistryActor>(m, "GateChemicalCountingActor")
      .def(py::init<py::dict &>())
      .def("SetMoleculeCounterId",
           &GateChemicalCountingActor::SetMoleculeCounterId)
      .def("GetNumberOfKilledParticles",
           &GateChemicalCountingActor::GetNumberOfKilledParticles)
      .def("GetNumberOfAbortedEvents",
           &GateChemicalCountingActor::GetNumberOfAbortedEvents)
      .def("GetNumberOfChemistryStarts",
           &GateChemicalCountingActor::GetNumberOfChemistryStarts)
      .def("GetNumberOfChemistryStages",
           &GateChemicalCountingActor::GetNumberOfChemistryStages)
      .def("GetNumberOfPreTimeStepCalls",
           &GateChemicalCountingActor::GetNumberOfPreTimeStepCalls)
      .def("GetNumberOfPostTimeStepCalls",
           &GateChemicalCountingActor::GetNumberOfPostTimeStepCalls)
      .def("GetNumberOfReactions",
           &GateChemicalCountingActor::GetNumberOfReactions)
      .def("GetNumberOfRecordedEvents",
           &GateChemicalCountingActor::GetNumberOfRecordedEvents)
      .def("GetAccumulatedPrimaryEnergyLoss",
           &GateChemicalCountingActor::GetAccumulatedPrimaryEnergyLoss)
      .def("GetAccumulatedEnergyDeposit",
           &GateChemicalCountingActor::GetAccumulatedEnergyDeposit)
      .def("GetMeanRestrictedLET",
           &GateChemicalCountingActor::GetMeanRestrictedLET)
      .def("GetStdRestrictedLET", &GateChemicalCountingActor::GetStdRestrictedLET)
      .def("GetSpeciesInfo", &GateChemicalCountingActor::GetSpeciesInfo)
      .def("GetRecordedTimes", &GateChemicalCountingActor::GetRecordedTimes)
      .def("RegisterConfiguredReactionCounter",
           &GateChemicalCountingActor::RegisterConfiguredReactionCounter)
      .def("GetConfiguredReactionCounterResults",
           &GateChemicalCountingActor::GetConfiguredReactionCounterResults)
      .def("RegisterConfiguredSpeciesCounter",
           &GateChemicalCountingActor::RegisterConfiguredSpeciesCounter)
      .def("GetConfiguredSpeciesCounterResults",
           &GateChemicalCountingActor::GetConfiguredSpeciesCounterResults);
}
