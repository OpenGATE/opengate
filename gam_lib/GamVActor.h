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
#include "GamVFilter.h"

namespace py = pybind11;

class GamVActor : public G4VPrimitiveScorer {

public:

    explicit GamVActor(py::dict &user_info);

    virtual ~GamVActor();

    virtual void AddActions(std::set<std::string> &actions);

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


    /*
     * WARNING WARNING WARNING WARNING
     *
     * In multithread mode, there is (for the moment) a single actor object shared by all threads.
     * It means it is **required** to use mutex when modifying a local variable.
     *
     * An alternative is to set all thread modifiable variables in a thread_local structure with
     * G4Cache<my_struct> (see for example in G4SingleParticleSource). And merge at the end.
     *
     * Another alternative is to use G4VAccumulable (not fully clear how/when to call Merge() however).
     *
     * Last alternative -> change python side to create one actor for each thread.
     * It takes more memory, but could be potentially faster (no lock).
     *
     * ... We left this as exercise for the reader ;)
     *
     */


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
    std::set<std::string> fActions;

    // Name of the mother volume
    std::string fMotherVolumeName;

    // List of active filters
    std::vector<GamVFilter *> fFilters;

};

#endif // GamVActor_h
