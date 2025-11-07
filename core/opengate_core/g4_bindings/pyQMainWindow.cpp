/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateConfiguration.h"

#if USE_VISU > 0
#include <qmainwindow.h>

void init_QMainWindow(py::module &m) {
  py::class_<QMainWindow>(m, "QMainWindow")
      .def("setVisible", &QMainWindow::setVisible);
}
#endif
