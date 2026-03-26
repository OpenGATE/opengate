/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateChemicalStageActor.h"

void init_GateChemicalStageActor(py::module &m) {
  py::class_<GateChemicalStageActor,
             std::unique_ptr<GateChemicalStageActor, py::nodelete>,
             GateVChemistryActor>(m, "GateChemicalStageActor")
      .def(py::init<py::dict &>())
      .def("SetMoleculeCounterId", &GateChemicalStageActor::SetMoleculeCounterId)
      .def("GetNumberOfKilledParticles",
           &GateChemicalStageActor::GetNumberOfKilledParticles)
      .def("GetNumberOfAbortedEvents",
           &GateChemicalStageActor::GetNumberOfAbortedEvents)
      .def("GetNumberOfChemistryStarts",
           &GateChemicalStageActor::GetNumberOfChemistryStarts)
      .def("GetNumberOfChemistryStages",
           &GateChemicalStageActor::GetNumberOfChemistryStages)
      .def("GetNumberOfPreTimeStepCalls",
           &GateChemicalStageActor::GetNumberOfPreTimeStepCalls)
      .def("GetNumberOfPostTimeStepCalls",
           &GateChemicalStageActor::GetNumberOfPostTimeStepCalls)
      .def("GetNumberOfReactions",
           &GateChemicalStageActor::GetNumberOfReactions)
      .def("GetNumberOfRecordedEvents",
           &GateChemicalStageActor::GetNumberOfRecordedEvents)
      .def("GetAccumulatedPrimaryEnergyLoss",
           &GateChemicalStageActor::GetAccumulatedPrimaryEnergyLoss)
      .def("GetAccumulatedEnergyDeposit",
           &GateChemicalStageActor::GetAccumulatedEnergyDeposit)
      .def("GetMeanRestrictedLET",
           &GateChemicalStageActor::GetMeanRestrictedLET)
      .def("GetStdRestrictedLET",
           &GateChemicalStageActor::GetStdRestrictedLET)
      .def("GetSpeciesInfo", &GateChemicalStageActor::GetSpeciesInfo)
      .def("GetReactionCounts", &GateChemicalStageActor::GetReactionCounts)
      .def("GetRecordedTimes", &GateChemicalStageActor::GetRecordedTimes);
}
