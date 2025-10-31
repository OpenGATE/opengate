/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include <algorithm>
#include <vector>

#include "FTFP_BERT.hh"
#include "FTFP_BERT_ATL.hh"
#include "FTFP_BERT_HP.hh"
#include "FTFP_BERT_TRV.hh"
#include "FTFP_INCLXX.hh"
#include "FTFP_INCLXX_HP.hh"
#include "FTF_BIC.hh"
#include "LBE.hh"

#include "NuBeam.hh"
#include "QBBC.hh"
#include "QGSP_BERT.hh"
#include "QGSP_BERT_HP.hh"
#include "QGSP_BIC.hh"
#include "QGSP_BIC_AllHP.hh"
#include "QGSP_BIC_HP.hh"
#include "QGSP_FTFP_BERT.hh"
#include "QGSP_INCLXX.hh"
#include "QGSP_INCLXX_HP.hh"
#include "QGS_BIC.hh"
#include "Shielding.hh"

#include "G4EmStandardPhysics.hh"
#include "G4EmStandardPhysics_option1.hh"
#include "G4EmStandardPhysics_option2.hh"
#include "G4EmStandardPhysics_option3.hh"
#include "G4EmStandardPhysics_option4.hh"

#include "G4EmDNAPhysics.hh"
#include "G4EmDNAPhysics_option1.hh"
#include "G4EmDNAPhysics_option2.hh"
#include "G4EmDNAPhysics_option3.hh"
#include "G4EmDNAPhysics_option4.hh"
#include "G4EmDNAPhysics_option5.hh"
#include "G4EmDNAPhysics_option6.hh"
#include "G4EmDNAPhysics_option7.hh"
#include "G4EmDNAPhysics_option8.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4EmLivermorePolarizedPhysics.hh"
#include "G4EmLowEPPhysics.hh"
#include "G4EmPenelopePhysics.hh"
#include "G4EmStandardPhysicsGS.hh"
#include "G4GenericBiasingPhysics.hh"
#include "G4OpticalPhysics.hh"

#include "G4DecayPhysics.hh"
#include "G4RadioactiveDecayPhysics.hh"

#include "G4VModularPhysicsList.hh"
#include "G4VPhysicsConstructor.hh"
#include "G4VUserPhysicsList.hh"

// macro for adding physics lists: no parameter
// #define ADD_PHYSICS_LIST0(m, plname) \
//   py::class_<plname, G4VModularPhysicsList>(m, #plname).def(py::init<>()); \
//   AddPhysicsList(#plname);

// macro for adding physics lists: one int parameter
// #define ADD_PHYSICS_LIST1(m, plname) \
//   py::class_<plname, G4VUserPhysicsList>(m, #plname).def(py::init<G4int>());
//   \ AddPhysicsList(#plname);

// macro for adding physics lists: int+str parameter
// #define ADD_PHYSICS_LIST2(m, plname) \
//   py::class_<plname, G4VUserPhysicsList>(m, #plname) \
//       .def(py::init<G4int, G4String>()); \
//   AddPhysicsList(#plname);

// macro for adding physics constructor: one int parameter (verbosity),
// nodelete is needed because the G4 run manager deletes the physics list
// on the cpp side, python should not delete the object
#define ADD_PHYSICS_CONSTRUCTOR(plname)                                        \
  py::class_<plname, G4VPhysicsConstructor,                                    \
             std::unique_ptr<plname, py::nodelete>>(m, #plname)                \
      .def(py::init<G4int>());

// FIXME ? A bit different for the biasing classe which do not take as argument
// a int. Moreover, we need at least the function PhysicsBias to put a bias, so
// this constructor needs probably its own function ?.
#define ADD_PHYSICS_CONSTRUCTOR_BIASING(plname)                                \
  py::class_<plname, G4VPhysicsConstructor,                                    \
             std::unique_ptr<plname, py::nodelete>>(m, #plname)                \
      .def(py::init())                                                         \
      .def("PhysicsBias",                                                      \
           py::overload_cast<const G4String &, const std::vector<G4String> &>( \
               &G4GenericBiasingPhysics::PhysicsBias),                         \
           py::return_value_policy::reference_internal)                        \
      .def("PhysicsBias",                                                      \
           py::overload_cast<const G4String &>(                                \
               &G4GenericBiasingPhysics::PhysicsBias),                         \
           py::return_value_policy::reference_internal)                        \
      .def("NonPhysicsBias",                                                   \
           py::overload_cast<const G4String &>(                                \
               &G4GenericBiasingPhysics::NonPhysicsBias),                      \
           py::return_value_policy::reference_internal);

namespace pyPhysicsLists {

static std::vector<std::string> plList;

void AddPhysicsList(const G4String &plname) {
  std::cout << "[pyg4bind11] AddPhysicsList " << plname << std::endl;
  plList.push_back(plname);
}

void ListPhysicsList() {
  for (auto &i : plList) {
    G4cout << i << G4endl;
  }
}

void ClearPhysicsList() {
  // G4cout << "Clear PL" << std::endl;
  plList.clear();
  // G4cout << "Clear PL ok" << std::endl;
}

} // namespace pyPhysicsLists

using namespace pyPhysicsLists;

void init_G4PhysicsLists(py::module &m) {

  m.def("ListPhysicsList", ListPhysicsList);
  m.def("ClearPhysicsList", ClearPhysicsList);

  // G4VUserPhysicsList
  // -> not use for now. Instead, py side use :
  // G4PhysListFactory GetReferencePhysList
  /*
  ADD_PHYSICS_LIST1(m, FTFP_BERT);
  ADD_PHYSICS_LIST1(m, FTFP_BERT_ATL);
  ADD_PHYSICS_LIST1(m, FTFP_BERT_HP);
  ADD_PHYSICS_LIST1(m, FTFP_BERT_TRV);
  ADD_PHYSICS_LIST1(m, FTFP_INCLXX);
  ADD_PHYSICS_LIST1(m, FTFP_INCLXX_HP);
  ADD_PHYSICS_LIST1(m, FTF_BIC);
  ADD_PHYSICS_LIST1(m, LBE);
  ADD_PHYSICS_LIST1(m, NuBeam);

  ADD_PHYSICS_LIST2(m, QBBC);

  ADD_PHYSICS_LIST1(m, QGSP_BERT);
  ADD_PHYSICS_LIST1(m, QGSP_BERT_HP);
  ADD_PHYSICS_LIST1(m, QGSP_BIC);
  ADD_PHYSICS_LIST1(m, QGSP_BIC_AllHP);
  ADD_PHYSICS_LIST1(m, QGSP_BIC_HP);
  ADD_PHYSICS_LIST1(m, QGSP_FTFP_BERT);
  ADD_PHYSICS_LIST1(m, QGSP_INCLXX);
  ADD_PHYSICS_LIST1(m, QGSP_INCLXX_HP);
  ADD_PHYSICS_LIST1(m, QGS_BIC);
  ADD_PHYSICS_LIST2(m, Shielding);
   */

  // G4VPhysicsConstructor
  ADD_PHYSICS_CONSTRUCTOR(G4EmStandardPhysics)
  ADD_PHYSICS_CONSTRUCTOR(G4EmStandardPhysics_option1)
  ADD_PHYSICS_CONSTRUCTOR(G4EmStandardPhysics_option2)
  ADD_PHYSICS_CONSTRUCTOR(G4EmStandardPhysics_option3)
  ADD_PHYSICS_CONSTRUCTOR(G4EmStandardPhysics_option4)

  ADD_PHYSICS_CONSTRUCTOR(G4EmStandardPhysicsGS)
  ADD_PHYSICS_CONSTRUCTOR(G4EmLowEPPhysics)
  ADD_PHYSICS_CONSTRUCTOR(G4EmLivermorePhysics)
  ADD_PHYSICS_CONSTRUCTOR(G4EmLivermorePolarizedPhysics)
  ADD_PHYSICS_CONSTRUCTOR(G4EmPenelopePhysics)
  ADD_PHYSICS_CONSTRUCTOR(G4EmDNAPhysics)
  ADD_PHYSICS_CONSTRUCTOR(G4EmDNAPhysics_option1)
  ADD_PHYSICS_CONSTRUCTOR(G4EmDNAPhysics_option2)
  ADD_PHYSICS_CONSTRUCTOR(G4EmDNAPhysics_option3)
  ADD_PHYSICS_CONSTRUCTOR(G4EmDNAPhysics_option4)
  ADD_PHYSICS_CONSTRUCTOR(G4EmDNAPhysics_option5)
  ADD_PHYSICS_CONSTRUCTOR(G4EmDNAPhysics_option6)
  ADD_PHYSICS_CONSTRUCTOR(G4EmDNAPhysics_option7)
  ADD_PHYSICS_CONSTRUCTOR(G4EmDNAPhysics_option8)
  ADD_PHYSICS_CONSTRUCTOR(G4OpticalPhysics)

  ADD_PHYSICS_CONSTRUCTOR(G4DecayPhysics)
  ADD_PHYSICS_CONSTRUCTOR(G4RadioactiveDecayPhysics)

  ADD_PHYSICS_CONSTRUCTOR_BIASING(G4GenericBiasingPhysics)

  // sort PL vector
  std::sort(plList.begin(), plList.end());
}
