/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateFastY90Kernel.h"
#include <algorithm>
#include <cstddef>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

namespace py = pybind11;

namespace {
template <std::size_t N>
py::array_t<double> CopyTable(const double (&values)[N]) {
  py::array_t<double> copy(static_cast<py::ssize_t>(N));
  std::copy(values, values + N, copy.mutable_data());
  return copy;
}

template <std::size_t Rows, std::size_t Cols>
py::array_t<double> CopyTable(const double (&values)[Rows][Cols]) {
  py::array_t<double> copy(
      {static_cast<py::ssize_t>(Rows), static_cast<py::ssize_t>(Cols)});
  for (std::size_t row = 0; row < Rows; ++row)
    std::copy(values[row], values[row] + Cols,
              copy.mutable_data() + row * Cols);
  return copy;
}
} // namespace

void init_GateFastY90Kernel(py::module &m) {
  py::class_<GateFastY90Kernel>(m, "GateFastY90Kernel")
      .def(py::init<double, double>(), py::arg("min_brem_energy") = 0.0,
           py::arg("positron_probability") = 3.186e-5)
      .def("GetBremsstrahlungYield", &GateFastY90Kernel::GetBremsstrahlungYield)
      .def("GetTotalYield", &GateFastY90Kernel::GetTotalYield)
      .def("GetEffectiveMinBremEnergy",
           &GateFastY90Kernel::GetEffectiveMinBremEnergy)
      .def("IsPositron", &GateFastY90Kernel::IsPositron)
      .def("SampleBremsstrahlungEnergy",
           &GateFastY90Kernel::SampleBremsstrahlungEnergy)
      .def("SamplePositronEnergy", &GateFastY90Kernel::SamplePositronEnergy)
      .def("SampleRange", &GateFastY90Kernel::SampleRange)
      .def("SampleAngle", &GateFastY90Kernel::SampleAngle)
      .def_static("GetTables", [] {
        py::dict tables;
        tables["mEnergyTable"] = CopyTable(GateFastY90Kernel::GetEnergyTable());
        tables["mRangeTable"] = CopyTable(GateFastY90Kernel::GetRangeTable());
        tables["mAngleTable"] = CopyTable(GateFastY90Kernel::GetAngleTable());
        tables["mPositronEnergyTable"] =
            CopyTable(GateFastY90Kernel::GetPositronEnergyTable());
        return tables;
      });
}
