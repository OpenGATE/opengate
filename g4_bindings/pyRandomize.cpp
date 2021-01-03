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
            .def(py::init())

        /*
        .def("setTheSeed",       f1_setTheSeed)
        .def("setTheSeed",       f2_setTheSeed)
        .staticmethod("setTheSeed")
        .def("getTheSeed",           &HepRandom::getTheSeed)
        .staticmethod("getTheSeed")
        .def("setTheSeeds",      f1_setTheSeeds)
        .def("setTheSeeds",      f2_setTheSeeds)
        .staticmethod("setTheSeeds")
        .def("getTheSeeds",      f_getTheSeeds)
        .staticmethod("getTheSeeds")
        .def("getTheTableSeeds", f_getTheTableSeeds)
        .staticmethod("getTheTableSeeds")
        // ---
        .def("getTheGenerator",     &HepRandom::getTheGenerator,
             return_value_policy<reference_existing_object>())
        .staticmethod("getTheGenerator")

        .def("getTheEngine",        &HepRandom::getTheEngine,
             return_value_policy<reference_existing_object>())
        .staticmethod("getTheEngine")
        .def("saveEngineStatus",    f1_saveEngineStatus)
        .def("saveEngineStatus",    f2_saveEngineStatus)
        .staticmethod("saveEngineStatus")
        .def("restoreEngineStatus", f1_restoreEngineStatus)
        .def("restoreEngineStatus", f2_restoreEngineStatus)
        .staticmethod("restoreEngineStatus")
        .def("showEngineStatus",    &HepRandom::showEngineStatus)
        .staticmethod("showEngineStatus")
        .def("createInstance",      &HepRandom::createInstance)
        .staticmethod("createInstance")
        */
            ;

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

