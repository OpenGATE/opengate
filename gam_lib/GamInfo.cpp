/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#ifdef G4MULTITHREADED
#include "G4MTRunManager.hh"
#else

#include "G4RunManager.hh"

#endif

class GamInfo {
public:
    static bool get_G4MULTITHREADED() {
#ifdef G4MULTITHREADED
        return true;
#else
        return false;
#endif
    }
};

void init_GamInfo(py::module &m) {
    py::class_<GamInfo>(m, "GamInfo")
        .def(py::init())
        .def("get_G4MULTITHREADED", &GamInfo::get_G4MULTITHREADED);
}

