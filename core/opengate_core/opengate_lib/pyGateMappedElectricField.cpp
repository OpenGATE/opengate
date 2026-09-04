/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGridInterpolator.h"
#include "GateMappedElectricField.h"
#include <G4ElectroMagneticField.hh>
#include <G4LogicalVolume.hh>
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

void init_GateMappedElectricField(py::module &m) {

  py::class_<GateMappedElectricField, G4ElectroMagneticField,
             std::unique_ptr<GateMappedElectricField, py::nodelete>>(
      m, "GateMappedElectricField")

      .def(py::init([](const G4LogicalVolume *logical_volume, int nx, int ny,
                       int nz, double x0, double y0, double z0, double dx,
                       double dy, double dz, DoubleArray Ex, DoubleArray Ey,
                       DoubleArray Ez,
                       GateGridInterpolator::InterpolationMethod interp) {
             GateGridInterpolator::GridDefinition gridDef{nx, ny, nz, x0, y0,
                                                          z0, dx, dy, dz};
             GateGridInterpolator::FieldValues fieldValues{
                 to_vec(Ex), to_vec(Ey), to_vec(Ez)};
             return new GateMappedElectricField(logical_volume, gridDef,
                                                fieldValues, interp);
           }),
           py::arg("logical_volume"), py::arg("nx"), py::arg("ny"),
           py::arg("nz"), py::arg("x0"), py::arg("y0"), py::arg("z0"),
           py::arg("dx"), py::arg("dy"), py::arg("dz"), py::arg("Ex"),
           py::arg("Ey"), py::arg("Ez"), py::arg("interpolation"));
}
