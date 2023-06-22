/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Run.hh"
#include "G4RunManager.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"

// A thin wrapper around the G4RunManager,
// to expose protected members from the G4RunManager class.
// More protected members can be exposed if needed.
class WrappedG4RunManager : public G4RunManager {
public:
  WrappedG4RunManager();
  virtual ~WrappedG4RunManager();

  static WrappedG4RunManager *GetRunManager();

  // move this protected member of G4RunManager into
  // the public portion of WrappedG4RunManager
  using G4RunManager::initializedAtLeastOnce;

  // Define getters/setters for the exposed member
  inline G4bool GetInitializedAtLeastOnce() {
    return G4RunManager::initializedAtLeastOnce;
  };
  inline void SetInitializedAtLeastOnce(G4bool tf) {
    G4RunManager::initializedAtLeastOnce = tf;
  };
  inline void FakeBeamOn() {
    // first argument=0 means fake run
    // second argument is pass to macro file -> null char = no macro
    // last argument disregarded if <0
    const char fakemacro = (char)0;
    G4RunManager::BeamOn(0, &fakemacro, -1);
    SetRunIDCounter(0);
  };
};
