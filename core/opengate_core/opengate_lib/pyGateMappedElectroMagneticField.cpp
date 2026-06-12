/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGridInterpolator.h"
#include "GateMappedElectroMagneticField.h"
#include <G4ElectroMagneticField.hh>
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

void init_GateMappedElectroMagneticField(py::module &m) {

  py::class_<GateMappedElectroMagneticField, G4ElectroMagneticField,
             std::unique_ptr<GateMappedElectroMagneticField, py::nodelete>>(
      m, "GateMappedElectroMagneticField")

      .def(py::init([](const G4VSolid *solid,
                       std::vector<G4ThreeVector> translations,
                       std::vector<G4RotationMatrix> rotations,
                       double delta_chord_mm, int nx_B, int ny_B, int nz_B,
                       double x0_B, double y0_B, double z0_B, double dx_B,
                       double dy_B, double dz_B, DoubleArray Bx, DoubleArray By,
                       DoubleArray Bz, int nx_E, int ny_E, int nz_E,
                       double x0_E, double y0_E, double z0_E, double dx_E,
                       double dy_E, double dz_E, DoubleArray Ex, DoubleArray Ey,
                       DoubleArray Ez,
                       GateGridInterpolator::InterpolationMethod interp) {
             GateGridInterpolator::GridDefinition gridDefB{
                 nx_B, ny_B, nz_B, x0_B, y0_B, z0_B, dx_B, dy_B, dz_B};
             GateGridInterpolator::FieldValues fieldValuesB{
                 to_vec(Bx), to_vec(By), to_vec(Bz)};
             GateGridInterpolator::GridDefinition gridDefE{
                 nx_E, ny_E, nz_E, x0_E, y0_E, z0_E, dx_E, dy_E, dz_E};
             GateGridInterpolator::FieldValues fieldValuesE{
                 to_vec(Ex), to_vec(Ey), to_vec(Ez)};
             return new GateMappedElectroMagneticField(
                 solid, translations, rotations, delta_chord_mm, gridDefB,
                 fieldValuesB, gridDefE, fieldValuesE, interp);
           }),
           py::arg("solid"), py::arg("translations"), py::arg("rotations"),
           py::arg("delta_chord_mm"), py::arg("nx_B"), py::arg("ny_B"),
           py::arg("nz_B"), py::arg("x0_B"), py::arg("y0_B"), py::arg("z0_B"),
           py::arg("dx_B"), py::arg("dy_B"), py::arg("dz_B"), py::arg("Bx"),
           py::arg("By"), py::arg("Bz"), py::arg("nx_E"), py::arg("ny_E"),
           py::arg("nz_E"), py::arg("x0_E"), py::arg("y0_E"), py::arg("z0_E"),
           py::arg("dx_E"), py::arg("dy_E"), py::arg("dz_E"), py::arg("Ex"),
           py::arg("Ey"), py::arg("Ez"), py::arg("interpolation"))

      .def("SetTransforms", &GateMappedElectroMagneticField::SetTransforms,
           py::arg("translations"), py::arg("rotations"));
}
