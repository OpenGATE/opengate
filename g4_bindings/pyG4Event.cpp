/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Event.hh"

void init_G4Event(py::module &m) {
    py::class_<G4Event>(m, "G4Event")
        .def(py::init<int>())
        .def("Print", &G4Event::Print)
        .def("Draw", &G4Event::Draw)
        .def("SetEventID", &G4Event::SetEventID)
        .def("GetEventID", &G4Event::GetEventID)
        .def("SetEventAborted", &G4Event::SetEventAborted)
        .def("IsAborted", &G4Event::IsAborted)
        .def("AddPrimaryVertex", &G4Event::AddPrimaryVertex)
        .def("GetNumberOfPrimaryVertex", &G4Event::GetNumberOfPrimaryVertex)
        .def("GetPrimaryVertex", &G4Event::GetPrimaryVertex, py::return_value_policy::reference_internal)
        .def("GetTrajectoryContainer", &G4Event::GetTrajectoryContainer, py::return_value_policy::reference_internal)
        .def("SetUserInformation", &G4Event::SetUserInformation)
        .def("GetUserInformation", &G4Event::GetUserInformation, py::return_value_policy::reference_internal);
}
