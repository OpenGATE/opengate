/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ChordFinder.hh"
#include "G4Field.hh"
#include "G4FieldManager.hh"
#include "G4MagneticField.hh"
#include "G4Track.hh"

void init_G4FieldManager(py::module &m) {
  py::class_<G4FieldManager, std::unique_ptr<G4FieldManager, py::nodelete>>(
      m, "G4FieldManager")

    .def(py::init<G4Field *, G4ChordFinder *, G4bool>())
    .def(py::init<G4MagneticField*>())


    .def("SetDetectorField", &G4FieldManager::SetDetectorField)
    .def("ProposeDetectorField", &G4FieldManager::ProposeDetectorField)
    .def("ChangeDetectorField", &G4FieldManager::ChangeDetectorField)
    .def("GetDetectorField", &G4FieldManager::GetDetectorField,
        py::return_value_policy::reference_internal)

    .def("DoesFieldExist", &G4FieldManager::DoesFieldExist)

    .def("CreateChordFinder", &G4FieldManager::CreateChordFinder)
    .def("SetChordFinder", &G4FieldManager::SetChordFinder)
    .def("GetChordFinder", py::overload_cast<>(&G4FieldManager::GetChordFinder),
        py::return_value_policy::reference_internal)    // TODO: check if this makes sense

    .def("ConfigureForTrack", &G4FieldManager::ConfigureForTrack)

    .def("SetGlobalFieldManager", &G4FieldManager::SetGlobalFieldManager)
    .def("GetGlobalFieldManager", &G4FieldManager::GetGlobalFieldManager,
        py::return_value_policy::reference_internal)

    .def("GetDeltaIntersection", &G4FieldManager::GetDeltaIntersection)
    .def("GetDeltaOneStep", &G4FieldManager::GetDeltaOneStep)
    .def("SetAccuraciesWithDeltaOneStep", &G4FieldManager::SetAccuraciesWithDeltaOneStep)
    .def("SetDeltaOneStep", &G4FieldManager::SetDeltaOneStep)
    .def("SetDeltaIntersection", &G4FieldManager::SetDeltaIntersection)

    .def("GetMinimumEpsilonStep", &G4FieldManager::GetMinimumEpsilonStep)
    .def("SetMinimumEpsilonStep", &G4FieldManager::SetMinimumEpsilonStep)
    .def("GetMaximumEpsilonStep", &G4FieldManager::GetMaximumEpsilonStep)
    .def("SetMaximumEpsilonStep", &G4FieldManager::SetMaximumEpsilonStep)

    .def("DoesFieldChangeEnergy", &G4FieldManager::DoesFieldChangeEnergy)
    .def("SetFieldChangesEnergy", &G4FieldManager::SetFieldChangesEnergy)

    .def("GetMaxAcceptedEpsilon", &G4FieldManager::GetMaxAcceptedEpsilon)
    .def("SetMaxAcceptedEpsilon", &G4FieldManager::SetMaxAcceptedEpsilon)
    ;
}
