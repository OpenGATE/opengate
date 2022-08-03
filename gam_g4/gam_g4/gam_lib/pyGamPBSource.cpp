/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamPBSource.h"

void init_GamPBSource(py::module &m) {

  py::class_<GamPBSource, GamGenericSource>(m, "GamPBSource")
      .def(py::init())
      .def("InitializeUserInfo", &GamPBSource::InitializeUserInfo);
}
