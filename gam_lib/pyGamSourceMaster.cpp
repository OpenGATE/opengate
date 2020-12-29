/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/chrono.h>

namespace py = pybind11;

#include "GamSourceMaster.h"
#include "GamVSource.h"

// Main wrapper
void init_GamSourceMaster(py::module &m) {

    py::class_<GamSourceMaster, G4VUserPrimaryGeneratorAction>(m, "GamSourceMaster")
            .def(py::init())
            .def("add_source", &GamSourceMaster::add_source)
            .def("initialize", &GamSourceMaster::initialize)
            .def("start", [](GamSourceMaster *sm) {
                py::gil_scoped_release release;
                sm->start();
            })
        /*.def("StartRun", [](GamSourceMaster *sm, int run_id) {
            py::gil_scoped_release release;
            sm->StartRun(run_id);
        })*/
            ;
}
