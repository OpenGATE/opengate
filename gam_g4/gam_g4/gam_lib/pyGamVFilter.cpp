/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamVFilter.h"
#include "GamHelpers.h"

/*
 * The "trampoline" functions below are required if we want to
 * allow callbacks on the py side.
 *
 * If it is not needed: to not define trampoline functions in class that inherit from VFilter.
 *
 * It must be defined also in all classes that inherit from GamVFilter
 *
 * Hence, BeginOfRunAction, BeginOfEventAction etc maybe define in py side
 * (but it will be slower, especially for steps)
 */

class PyGamVFilter : public GamVFilter {
public:
    // Inherit the constructors
    using GamVFilter::GamVFilter;

    void Initialize(py::dict &user_info) override {
        PYBIND11_OVERLOAD(void, GamVFilter, Initialize, user_info);
    }

    bool Accept(const G4Step *step) const override {
        PYBIND11_OVERLOAD(bool, GamVFilter, Accept, step);
    }
};

void init_GamVFilter(py::module &m) {

    py::class_<GamVFilter, PyGamVFilter>(m, "GamVFilter")
        .def(py::init())
        .def("Initialize", &GamVFilter::Initialize);
}

