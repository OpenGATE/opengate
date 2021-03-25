/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamVActor_h
#define GamVActor_h

#include <pybind11/stl.h>
#include "G4VPrimitiveScorer.hh"
#include "G4Event.hh"
#include "G4Run.hh"

namespace py = pybind11;

class GamVActor : public G4VPrimitiveScorer {

public:

    explicit GamVActor(py::dict &user_info);

    virtual ~GamVActor();

    // Called at initialisation
    virtual void ActorInitialize() {}

    // Used to add a callback to a given volume.
    // Every step in this volume will trigger a SteppingAction
    void RegisterSD(G4LogicalVolume *lv);

    // Called when the simulation start
    virtual void StartSimulationAction() {}

    // Called when the simulation end
    virtual void EndSimulationAction() {}

    // Called by Geant4 every hits. Call SteppingAction and return True
    virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

    // Called every ProcessHits, should be overloaded
    virtual void SteppingAction(G4Step *, G4TouchableHistory *) {}

    // Called every time a Run starts
    virtual void BeginOfRunAction(const G4Run * /*run*/) {}

    // Called every time a Run ends
    virtual void EndOfRunAction(const G4Run * /*run*/) {}

    // Called every time an Event starts
    virtual void BeginOfEventAction(const G4Event * /*event*/) {}

    // Called every time an Event ends
    virtual void EndOfEventAction(const G4Event * /*event*/) {}

    // Called every time a Track starts
    virtual void PreUserTrackingAction(const G4Track */*track*/) {}

    // Called every time a Track ends
    virtual void PostUserTrackingAction(const G4Track */*track*/) {}

    // List of actions (set to trigger some actions)
    // Can be set either on cpp or py side
    std::vector<std::string> fActions;

};

#endif // GamVActor_h
