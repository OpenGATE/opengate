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
#include "G4Field.hh"


// Trampoline class to allow Python to override GetFieldValue for
// electromagnetic fields.
class PyG4ElectroMagneticField : public G4ElectroMagneticField {
public:
  using G4ElectroMagneticField::G4ElectroMagneticField;

  void GetFieldValue(const G4double Point[4], G4double *field) const override {
    py::gil_scoped_acquire gil;

    // Convert Point to Python list
    py::list pyPoint;
    pyPoint.append(Point[0]);
    pyPoint.append(Point[1]);
    pyPoint.append(Point[2]);
    pyPoint.append(Point[3]);

    // Try to get the Python override
    py::function override = py::get_override(this, "GetFieldValue");
    if (override) {
      // Call Python implementation and expect [Bx, By, Bz, Ex, Ey, Ez]
      py::object result = override(pyPoint);
      if (!result.is_none()) {
        py::list field_list = result.cast<py::list>();
        size_t n = py::len(field_list)

        if (n != 6) {
          throw std::invalid_argument(
              "GetFieldValue for G4ElectroMagneticField must return exactly 6 components [Bx, By, Bz, Ex, Ey, Ez]");
        }

        for (size_t i = 0; i < n && i < 6; ++i) {
          field[i] = field_list[i].cast<G4double>();
        }

      }
    }
  }

  G4bool DoesFieldChangeEnergy() const override {
    PYBIND11_OVERRIDE_PURE(
        G4bool,
        G4ElectroMagneticField,
        DoesFieldChangeEnergy
    );
  }
};

void init_G4ElectroMagneticField(py::module &m) {

  py::class_<G4ElectroMagneticField, G4Field, PyG4ElectroMagneticField,
             std::unique_ptr<G4ElectroMagneticField, py::nodelete>>(
      m, "G4ElectroMagneticField")

      .def(py::init<>())

      .def("DoesFieldChangeEnergy",
           &G4ElectroMagneticField::DoesFieldChangeEnergy)

      ;
}
