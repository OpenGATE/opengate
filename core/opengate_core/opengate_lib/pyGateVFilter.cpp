/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateHelpers.h"
#include "GateVFilter.h"

/*
 * The "trampoline" functions below are required if we want to
 * allow callbacks on the py side.
 *
 * If it is not needed: to not define trampoline functions in class that inherit
 * from VFilter.
 *
 * It must be defined also in all classes that inherit from GateVFilter
 *
 * Hence, BeginOfRunAction, BeginOfEventAction etc maybe define in py side
 * (but it will be slower, especially for steps)
 */

class PyGateVFilter : public GateVFilter {
public:
  // Inherit the constructors
  using GateVFilter::GateVFilter;

  void Initialize(py::dict &user_info) override {
    PYBIND11_OVERLOAD(void, GateVFilter, Initialize, user_info);
  }

  bool Accept(G4Step *step) const override {
    PYBIND11_OVERLOAD(bool, GateVFilter, Accept, step);
  }

  bool Accept(const G4Event *event) const override {
    PYBIND11_OVERLOAD(bool, GateVFilter, Accept, event);
  }

  bool Accept(const G4Track *track) const override {
    PYBIND11_OVERLOAD(bool, GateVFilter, Accept, track);
  }

  bool Accept(const G4Run *run) const override {
    PYBIND11_OVERLOAD(bool, GateVFilter, Accept, run);
  }
};

void init_GateVFilter(py::module &m) {

  py::class_<GateVFilter, PyGateVFilter>(m, "GateVFilter")
      .def(py::init())
      .def("Initialize", &GateVFilter::Initialize);
}
