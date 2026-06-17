/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateChemistryWorld.h"

#include "G4ThreeVector.hh"
#include "pybind11/pybind11.h"

#include <stdexcept>

namespace py = pybind11;

void init_GateChemistryWorld(py::module &m) {
  py::class_<GateChemistryWorld>(m, "GateChemistryWorld")
      .def(py::init<>())
      .def(
          "SetChemistryBoundary",
          [](GateChemistryWorld &self, py::sequence translation,
             py::sequence halfSize) {
            if (py::len(translation) != 3 || py::len(halfSize) != 3) {
              throw std::runtime_error(
                  "SetChemistryBoundary expects two 3-vectors.");
            }
            self.SetChemistryBoundary(
                G4ThreeVector(translation[0].cast<G4double>(),
                              translation[1].cast<G4double>(),
                              translation[2].cast<G4double>()),
                G4ThreeVector(halfSize[0].cast<G4double>(),
                              halfSize[1].cast<G4double>(),
                              halfSize[2].cast<G4double>()));
          },
          py::arg("translation"), py::arg("half_size"))
      .def("ConstructChemistryBoundary",
           &GateChemistryWorld::ConstructChemistryBoundary)
      .def("ConstructChemistryComponents",
           &GateChemistryWorld::ConstructChemistryComponents)
      .def("ClearChemicalComponents",
           &GateChemistryWorld::ClearChemicalComponents)
      .def("AddChemicalComponent", &GateChemistryWorld::AddChemicalComponent,
           py::arg("molecule_name"), py::arg("concentration"))
      .def("SetPH", &GateChemistryWorld::SetPH, py::arg("pH"))
      .def("GetPH", &GateChemistryWorld::GetPH);
}
