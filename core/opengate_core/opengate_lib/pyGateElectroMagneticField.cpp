/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4ElectroMagneticField.hh"
#include "G4VSolid.hh"
#include "GateElectroMagneticField.h"

void init_GateElectroMagneticField(py::module &m) {
  py::class_<GateElectroMagneticField, G4ElectroMagneticField,
             std::unique_ptr<GateElectroMagneticField, py::nodelete>>(
      m, "GateElectroMagneticField")

      .def(py::init([](G4ElectroMagneticField *inner, const G4VSolid *solid,
                       std::vector<G4ThreeVector> translations,
                       std::vector<G4RotationMatrix> rotations,
                       double delta_chord_mm) {
             return new GateElectroMagneticField(inner, solid, translations,
                                                 rotations, delta_chord_mm);
           }),
           py::arg("inner_field"), py::arg("solid"), py::arg("translations"),
           py::arg("rotations"), py::arg("delta_chord_mm"))

      .def("SetTransforms", &GateElectroMagneticField::SetTransforms,
           py::arg("translations"), py::arg("rotations"),
           "Replace the cached world-to-local transforms. Call between runs "
           "only after dynamic geometry changes have been applied.");
}
