/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "G4MTRunManager.hh"
#include "G4RunManager.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"

namespace py = pybind11;

// A thin wrapper around the G4RunManager,
// to expose protected members from the G4RunManager class.
// More protected members can be exposed if needed.
class WrappedG4MTRunManager : public G4MTRunManager {
public:
  WrappedG4MTRunManager();
  virtual ~WrappedG4MTRunManager();

  // move this protected member of G4RunManager into
  // the public portion of WrappedG4MTRunManager
  using G4MTRunManager::initializedAtLeastOnce;

  // Define getters/setters for the exposed member
  inline G4bool GetInitializedAtLeastOnce() {
    return G4MTRunManager::initializedAtLeastOnce;
  };
  inline void SetInitializedAtLeastOnce(G4bool tf) {
    G4MTRunManager::initializedAtLeastOnce = tf;
  };
  inline void InitializeWithoutFakeRun() { G4RunManager::Initialize(); }
  inline void FakeBeamOn() {
    // first argument=0 means fake run
    // second argument is pass to macro file -> null char = no macro
    // last argument disregarded if <0
    const char fakemacro = (char)0;
    G4MTRunManager::BeamOn(0, &fakemacro, -1);
    SetRunIDCounter(0);
  }
};
