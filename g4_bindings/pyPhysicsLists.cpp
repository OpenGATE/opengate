/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include <vector>
#include <algorithm>

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

#include "G4VUserPhysicsList.hh"
#include "G4VModularPhysicsList.hh"

// macro for adding physics lists: no parameter
#define ADD_PHYSICS_LIST0(m, plname)                    \
  py::class_<plname, G4VModularPhysicsList>(m, #plname) \
  .def(py::init<>());                                   \
  AddPhysicsList(#plname);


// FIXME G4VModularPhysicsList or G4VUserPhysicsList ?
// FIXME noncopyable ?

// macro for adding physics lists: one int parameter
#define ADD_PHYSICS_LIST1(m, plname)                    \
  py::class_<plname, G4VUserPhysicsList>(m, #plname) \
  .def(py::init<G4int>());                              \
  AddPhysicsList(#plname);

// macro for adding physics lists: int+str parameter
#define ADD_PHYSICS_LIST2(m, plname)                    \
  py::class_<plname, G4VUserPhysicsList>(m, #plname) \
  .def(py::init<G4int,G4String>());                     \
  AddPhysicsList(#plname);

namespace pyPhysicsLists {

    static std::vector<std::string> plList;

    void AddPhysicsList(const G4String &plname) {
        //std::cout << "[pyg4bind11] AddPhysicsList " << plname << std::endl;
        plList.push_back(plname);
    }

    void ListPhysicsList() {
        for (unsigned int i = 0; i < plList.size(); i++) {
            G4cout << plList[i] << G4endl;
        }
    }

}

using namespace pyPhysicsLists;

void init_G4PhysicsLists(py::module &m) {

    m.def("ListPhysicsList", ListPhysicsList);

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

    // sort PL vector
    std::sort(plList.begin(), plList.end());
}
