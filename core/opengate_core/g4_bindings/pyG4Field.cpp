/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4Field.hh"

/*
 * Trampoline class to allow Python to override GetFieldValue and
 * DoesFieldChangeEnergy. This enables users to define custom fields in Python.
 *
 * The GetFieldValue method receives a point (x, y, z, t) and must return
 * the field components at that point. The number of components depends on
 * the field type:
 *   - Magnetic field: 3 components (Bx, By, Bz)
 *   - Electric field: 3 components (Ex, Ey, Ez) at indices 3-5
 *   - Electromagnetic field: 6 components (Bx, By, Bz, Ex, Ey, Ez)
 */
class PyG4Field : public G4Field {
public:
  // Inherit the constructors
  using G4Field::G4Field;

  void GetFieldValue(const G4double Point[4], G4double *fieldArr) const override {
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
      // Call Python implementation and expect a list back
      py::object result = override(pyPoint);
      if (!result.is_none()) {
        py::list field_list = result.cast<py::list>();
        size_t n = py::len(field_list);
        for (size_t i = 0; i < n && i < G4Field::MAX_NUMBER_OF_COMPONENTS; ++i) {
          fieldArr[i] = field_list[i].cast<G4double>();
        }
      }
    }
  }

  G4bool DoesFieldChangeEnergy() const override {
    PYBIND11_OVERRIDE_PURE(
        G4bool,
        G4Field,
        DoesFieldChangeEnergy
    );
  }
};

void init_G4Field(py::module &m) {

  py::class_<G4Field, PyG4Field, std::unique_ptr<G4Field, py::nodelete>>(
      m, "G4Field")

      .def(py::init<G4bool>())
      .def(py::init<>())

      .def("DoesFieldChangeEnergy", &G4Field::DoesFieldChangeEnergy)
      .def("IsGravityActive", &G4Field::IsGravityActive)
      .def("SetGravityActive", &G4Field::SetGravityActive)

      ;
}
