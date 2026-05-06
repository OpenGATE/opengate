/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

#include "GateGridInterpolator.h"

namespace py = pybind11;

// exposes the interpolation method enum
void init_GateGridInterpolator(py::module &m) {
  py::enum_<GateGridInterpolator::InterpolationMethod>(
      m, "GateGridInterpolationMethod")
      .value("Nearest", GateGridInterpolator::InterpolationMethod::Nearest)
      .value("Trilinear", GateGridInterpolator::InterpolationMethod::Trilinear)
      .export_values();
}
