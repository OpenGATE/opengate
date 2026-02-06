/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4ElectricField.hh"
#include "G4ElectroMagneticField.hh"

// Trampoline class to allow Python to override GetFieldValue for electric
// fields. Inherits from G4ElectricField which already implements
// DoesFieldChangeEnergy() = true.
class PyG4ElectricField : public G4ElectricField {
public:
  using G4ElectricField::G4ElectricField;

  void GetFieldValue(const G4double Point[4], G4double *field) const override {
    py::gil_scoped_acquire gil;

    // Convert Point to Python list
    py::list pyPoint;
    pyPoint.append(Point[0]);
    pyPoint.append(Point[1]);
    pyPoint.append(Point[2]);
    pyPoint.append(Point[3]);

    // Get the Python override
    py::function override = py::get_override(this, "GetFieldValue");
    if (override) {
      py::object result = override(pyPoint);

      if (!result.is_none()) {
        py::list field_list = result.cast<py::list>();

        if (py::len(field_list) != 3) {
          throw std::invalid_argument(
              "GetFieldValue for G4ElectricField must return exactly 3 "
              "components [Ex, Ey, Ez]");
        }

        // User returned [Ex, Ey, Ez]
        field[0] = 0.;
        field[1] = 0.;
        field[2] = 0.;
        field[3] = field_list[0].cast<G4double>();
        field[4] = field_list[1].cast<G4double>();
        field[5] = field_list[2].cast<G4double>();
      }
    }
  }
};

void init_G4ElectricField(py::module &m) {

  py::class_<G4ElectricField, G4ElectroMagneticField, PyG4ElectricField,
             std::unique_ptr<G4ElectricField, py::nodelete>>(m,
                                                             "G4ElectricField")

      .def(py::init<>())

      .def("DoesFieldChangeEnergy", &G4ElectricField::DoesFieldChangeEnergy)

      ;
}
