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
#include "G4MagneticField.hh"

/*
 * Trampoline class to allow Python to override GetFieldValue for magnetic
 * fields. Inherits from G4MagneticField which already implements
 * DoesFieldChangeEnergy() = false.
 *
 * The GetFieldValue method receives a point (x, y, z, t) and must return
 * the magnetic field vector (Bx, By, Bz) at that point.
 */
class PyG4MagneticField : public G4MagneticField {
public:
  using G4MagneticField::G4MagneticField;

  void GetFieldValue(const G4double Point[4], G4double *Bfield) const override {
    // Always initialize output to a safe value.
    Bfield[0] = 0.;
    Bfield[1] = 0.;
    Bfield[2] = 0.;

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
      py::object result = override(pyPoint);
      if (!result.is_none()) {
        py::sequence bfield_seq = result.cast<py::sequence>();

        if (py::len(bfield_seq) != 3) {
          throw std::invalid_argument(
              "GetFieldValue for G4MagneticField must return exactly 3 "
              "components [Bx, By, Bz]");
        }

        Bfield[0] = bfield_seq[0].cast<G4double>();
        Bfield[1] = bfield_seq[1].cast<G4double>();
        Bfield[2] = bfield_seq[2].cast<G4double>();
      }
    }
  }
};

void init_G4MagneticField(py::module &m) {

  py::class_<G4MagneticField, G4Field, PyG4MagneticField,
             std::unique_ptr<G4MagneticField, py::nodelete>>(m,
                                                             "G4MagneticField")

      .def(py::init<>())

      .def("DoesFieldChangeEnergy", &G4MagneticField::DoesFieldChangeEnergy)

      ;
}
