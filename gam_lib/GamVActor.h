/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVActor_h
#define GateVActor_h

#include "G4VPrimitiveScorer.hh"
#include "G4Event.hh"
#include "G4Run.hh"

class GamVActor : public G4VPrimitiveScorer {

public:

    GamVActor(std::string name);

    virtual ~GamVActor();

    // Can be called once, at initialisation
    virtual void BeforeStart();

    // Called by Geant4 every hits
    virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

    // Called every hits, trigger SteppingBatchAction if batch is full
    virtual void ProcessHitsPerBatch(bool force = false);

    void RegisterSD(G4LogicalVolume *logical_volume);

    // Called every time an Event starts
    virtual void BeginOfEventAction(const G4Event * /*event*/) {}

    // Called every time an Event ends
    virtual void EndOfEventAction(const G4Event * /*event*/) {}

    // Called every time a batch of step must be processed
    virtual void SteppingBatchAction() {}

    // Called every time a Run ends. By default: process the remaining batch
    virtual void EndOfRunAction(const G4Run *run);

    /*
     virtual void BeginOfRunAction(const G4Run * run);
     virtual void BeginOfRunAction(const G4Run * run);
     */

    std::vector<std::string> actions;
    int batch_step_count;
    int batch_size;

protected:
    //G4MultiFunctionalDetector *mfd;
    std::vector<G4LogicalVolume *> logicalVolumes;
};

#endif // GateVActor_h
