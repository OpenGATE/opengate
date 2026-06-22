/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGridInterpolator.h"
#include "GateMappedMagneticField.h"
#include <G4MagneticField.hh>
#include <G4VSolid.hh>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

namespace {
using DoubleArray =
    py::array_t<double, py::array::c_style | py::array::forcecast>;

std::vector<double> to_vec(const DoubleArray &arr) {
  auto buf = arr.request();
  return std::vector<double>(static_cast<double *>(buf.ptr),
                             static_cast<double *>(buf.ptr) + buf.size);
}
} // namespace

void init_GateMappedMagneticField(py::module &m) {

  py::class_<GateMappedMagneticField, G4MagneticField,
             std::unique_ptr<GateMappedMagneticField, py::nodelete>>(
      m, "GateMappedMagneticField")

      .def(py::init([](const G4VSolid *solid,
                       std::vector<G4ThreeVector> translations,
                       std::vector<G4RotationMatrix> rotations,
                       double delta_chord_mm, int nx, int ny, int nz, double x0,
                       double y0, double z0, double dx, double dy, double dz,
                       DoubleArray Bx, DoubleArray By, DoubleArray Bz,
                       GateGridInterpolator::InterpolationMethod interp) {
             GateGridInterpolator::GridDefinition gridDef{nx, ny, nz, x0, y0,
                                                          z0, dx, dy, dz};
             GateGridInterpolator::FieldValues fieldValues{
                 to_vec(Bx), to_vec(By), to_vec(Bz)};
             return new GateMappedMagneticField(solid, translations, rotations,
                                                delta_chord_mm, gridDef,
                                                fieldValues, interp);
           }),
           py::arg("solid"), py::arg("translations"), py::arg("rotations"),
           py::arg("delta_chord_mm"), py::arg("nx"), py::arg("ny"),
           py::arg("nz"), py::arg("x0"), py::arg("y0"), py::arg("z0"),
           py::arg("dx"), py::arg("dy"), py::arg("dz"), py::arg("Bx"),
           py::arg("By"), py::arg("Bz"), py::arg("interpolation"))

      .def("SetTransforms", &GateMappedMagneticField::SetTransforms,
           py::arg("translations"), py::arg("rotations"));
}
