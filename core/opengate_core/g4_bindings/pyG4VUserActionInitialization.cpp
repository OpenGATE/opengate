/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Event.hh"
#include "G4SteppingVerbose.hh"
#include "G4UserEventAction.hh"
#include "G4UserRunAction.hh"
#include "G4UserStackingAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4UserTrackingAction.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserPrimaryGeneratorAction.hh"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// Needed helper class because of the pure virtual method
class PyG4VUserActionInitialization : public G4VUserActionInitialization {
public:
  // Inherit the constructors
  using G4VUserActionInitialization::G4VUserActionInitialization;
  // using G4VUserActionInitialization::SetUserAction;

  // Trampoline (need one for each virtual function)
  void Build() const override {
    PYBIND11_OVERLOAD_PURE(void, G4VUserActionInitialization, Build, );
  }

  // Trampoline (need one for each virtual function)
  void BuildForMaster() const override {
    PYBIND11_OVERLOAD(void, G4VUserActionInitialization, BuildForMaster, );
  }

  // Trampoline (need one for each virtual function)
  /*
  void G4VSteppingVerbose* InitializeSteppingVerbose() const override {
    PYBIND11_OVERLOAD(G4VSteppingVerbose*,
                      G4VUserActionInitialization,
                      InitializeSteppingVerbose,
                      );
  }
  */

  // Trampoline needed for protected  + overloaded function
  void SetUserAction(G4UserRunAction *e) {
    // std::cout << "PyG4VUserActionInitialization::SetUserActionRun" <<
    // std::endl; std::cout << "run " << e->IsMaster() << std::endl;
    G4VUserActionInitialization::SetUserAction(e);
  }

  void SetUserAction(G4VUserPrimaryGeneratorAction *e) {
    // std::cout << "PyG4VUserActionInitialization::SetUserAction" << std::endl;
    G4VUserActionInitialization::SetUserAction(e);
  }

  void SetUserAction(G4UserEventAction *e) {
    // std::cout << "PyG4VUserActionInitialization::SetUserAction" << std::endl;
    G4VUserActionInitialization::SetUserAction(e);
  }

  void SetUserAction(G4UserTrackingAction *e) {
    // std::cout << "PyG4VUserActionInitialization::SetUserAction" << std::endl;
    G4VUserActionInitialization::SetUserAction(e);
  }

  void SetUserAction(G4UserStackingAction *e) {
    // std::cout << "PyG4VUserActionInitialization::SetUserAction" << std::endl;
    G4VUserActionInitialization::SetUserAction(e);
  }

  void SetUserAction(G4UserSteppingAction *e) {
    // std::cout << "PyG4VUserActionInitialization::SetUserAction" << std::endl;
    G4VUserActionInitialization::SetUserAction(e);
  }
};

void init_G4VUserActionInitialization(py::module &m) {

  py::class_<G4VUserActionInitialization,
             std::unique_ptr<G4VUserActionInitialization, py::nodelete>,
             PyG4VUserActionInitialization>(m, "G4VUserActionInitialization")
      .def(py::init_alias())

      // Virtual method to be implemented by the user to instantiate user action
      .def("Build", &G4VUserActionInitialization::Build)

      // Virtual method to be implemented by the user to instantiate user run
      // action class object to be used by G4MTRunManager. This method is not
      // invoked in the sequential mode. The user should not use this method to
      // instantiate user action classes rather than user run action.
      .def("BuildForMaster", &G4VUserActionInitialization::BuildForMaster)

      // Virtual method to be implemented by the user if (s)he has a concrete
      // SteppingVerbose class to be used by the worker thread. In this case
      // (s)he should instantiate her/his SteppingVerbose in the concrete
      // implementation of this method and return its pointer. If this method is
      // not implemented, the default G4SteppingVerbose will be used. Please
      // note that this method affects only for the worker thread.
      .def("InitializeSteppingVerbose",
           &G4VUserActionInitialization::InitializeSteppingVerbose)

      /*.def("__del__",
           [](const G4VUserActionInitialization &s) -> void {
               std::cerr << "---------------> deleting
         G4VUserActionInitialization " << std::endl;
           })
           */

      .def("SetUserAction",
           (void(G4VUserActionInitialization::*)(G4UserRunAction *)) &
               PyG4VUserActionInitialization::SetUserAction)

      .def("SetUserAction",
           (void(G4VUserActionInitialization::*)(G4UserTrackingAction *)) &
               PyG4VUserActionInitialization::SetUserAction)

      .def("SetUserAction",
           (void(G4VUserActionInitialization::*)(G4UserStackingAction *)) &
               PyG4VUserActionInitialization::SetUserAction)

      .def("SetUserAction",
           (void(G4VUserActionInitialization::*)(G4UserEventAction *)) &
               PyG4VUserActionInitialization::SetUserAction)

      .def("SetUserAction", (void(G4VUserActionInitialization::*)(
                                G4VUserPrimaryGeneratorAction *)) &
                                PyG4VUserActionInitialization::SetUserAction)

      .def("SetUserAction",
           (void(G4VUserActionInitialization::*)(G4UserSteppingAction *)) &
               PyG4VUserActionInitialization::SetUserAction);
}
