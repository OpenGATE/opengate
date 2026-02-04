/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4FieldManager.hh"

void init_G4FieldManager(py::module &m) {
  py::class_<G4FieldManager, std::unique_ptr<G4FieldManager, py::nodelete>>(
      m, "G4FieldManager")

    .def(py::init<G4Field *, G4ChordFinder *, G4bool>())
    .def(py::init<G4MagneticField*>())


    .def("SetDetectorField", &G4LogicalVolume::SetDetectorField)
    .def("ProposeDetectorField", &G4LogicalVolume::ProposeDetectorField);
    .def("ChangeDetectorField", &G4LogicalVolume::ChangeDetectorField);
    .def("GetDetectorField", &G4LogicalVolume::GetDetectorField,
        py::return_value_policy::reference_internal);

    .def("DoesFieldExist", &G4LogicalVolume::DoesFieldExist);

    .def("CreateChordFinder", &G4LogicalVolume::CreateChordFinder);
    .def("SetChordFinder", &G4LogicalVolume::SetChordFinder);
    .def("GetChordFinder", &G4LogicalVolume::GetChordFinder,
        py::return_value_policy::reference_internal);

    .def("ConfigureForTrack", &G4LogicalVolume::ConfigureForTrack);

    .def("SetGlobalFieldManager", &G4LogicalVolume::SetGlobalFieldManager);
    .def("GetGlobalFieldManager", &G4LogicalVolume::GetGlobalFieldManager,
        py::return_value_policy::reference_internal);

    .def("GetDeltaIntersection", &G4LogicalVolume::GetDeltaIntersection);
    .def("GetDeltaOneStep", &G4LogicalVolume::GetDeltaOneStep);
    .def("SetAccuraciesWithDeltaOneStep", &G4LogicalVolume::SetAccuraciesWithDeltaOneStep);
    .def("SetDeltaOneStep", &G4LogicalVolume::SetDeltaOneStep);
    .def("SetDeltaIntersection", &G4LogicalVolume::SetDeltaIntersection);

    .def("GetMinimumEpsilonStep", &G4LogicalVolume::GetMinimumEpsilonStep);
    .def("SetMinimumEpsilonStep", &G4LogicalVolume::SetMinimumEpsilonStep);
    .def("GetMaximumEpsilonStep", &G4LogicalVolume::GetMaximumEpsilonStep);
    .def("SetMaximumEpsilonStep", &G4LogicalVolume::SetMaximumEpsilonStep);

    .def("DoesFieldChangeEnergy", &G4LogicalVolume::DoesFieldChangeEnergy);
    .def("SetFieldChangesEnergy", &G4LogicalVolume::SetFieldChangesEnergy);

    .def("GetMaxAcceptedEpsilon", &G4LogicalVolume::GetMaxAcceptedEpsilon);
    .def("SetMaxAcceptedEpsilon", &G4LogicalVolume::SetMaxAcceptedEpsilon);

    .def("InitialiseFieldChangesEnergy", &G4LogicalVolume::InitialiseFieldChangesEnergy);

    .def("ReportBadEpsilonValue", &G4LogicalVolume::ReportBadEpsilonValue);

}
