/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "Randomize.hh"
#include <vector>

using namespace CLHEP;

// G4UniformRand
double f_G4UniformRand() { return G4UniformRand(); }

void init_Randomize(py::module &m) {
    py::class_<HepRandom>(m, "G4Random")

        .def(py::init<long>())
        .def(py::init<HepRandomEngine &>())
        .def(py::init<HepRandomEngine *>())
        .def("setTheEngine", &HepRandom::setTheEngine)
        .def("showEngineStatus", &HepRandom::showEngineStatus)
        .def("getTheSeed", &HepRandom::getTheSeed)
        .def("setTheSeeds", &HepRandom::setTheSeeds);

    py::class_<HepRandomEngine>(m, "HepRandomEngine");

    py::class_<MTwistEngine, HepRandomEngine>(m, "MTwistEngine")
        .def(py::init());

    py::class_<MixMaxRng, HepRandomEngine>(m, "MixMaxRng")
        .def(py::init());


    // ---
    /*
    class_<RandBit, boost::noncopyable>
      ("RandBit", "generate bit random number", no_init)
      .def("shootBit", f1_RandBit_shootBit)
      .staticmethod("shootBit")
      ;
    */

    // ---
    /*
    class_<G4RandGauss, boost::noncopyable>
      ("G4RandGauss", "generate gaussian random number", no_init)
      .def("shoot", f1_RandGaussQ_shoot)
      .def("shoot", f2_RandGaussQ_shoot)
      .staticmethod("shoot")
      ;
    */

    // ---
    m.def("G4UniformRand", f_G4UniformRand);


}

