/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateAttributeComparisonFilter.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

template <typename T>
void make_attribute_filter_binding(py::module &m, const char *name) {
  py::class_<GateAttributeComparisonFilter<T>, GateVFilter>(m, name)
      .def(py::init())
      .def("InitializeUserInfo",
           &GateAttributeComparisonFilter<T>::InitializeUserInfo);
}

void init_GateAttributeComparisonFilter(py::module &m) {
  // These names must match what you use in filters.py (e.g.,
  // g4.GateAttributeFilterDouble)
  make_attribute_filter_binding<double>(m, "GateAttributeFilterDouble");
  make_attribute_filter_binding<int>(m, "GateAttributeFilterInt");
  make_attribute_filter_binding<std::string>(m, "GateAttributeFilterString");
}