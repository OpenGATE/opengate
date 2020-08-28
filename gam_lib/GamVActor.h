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

    virtual void BeforeStart();

    virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

    void RegisterSD(G4LogicalVolume *logical_volume);

    // do nothing by default will be overwritten
    virtual void BeginOfEventAction(const G4Event *event);

    virtual void EndOfEventAction(const G4Event *event);

    /*virtual void BeginOfRunAction(const G4Run * run);
    virtual void EndOfRunAction(const G4Run * run);
    virtual void BeginOfRunAction(const G4Run * run);
     */
    virtual void EndOfRunAction(const G4Run * /*run*/) {}

    // This function should be overwritten if batch processing
    virtual void SteppingBatchAction();

    // FIXME all others
    void ProcessBatch(bool force = false);

    std::vector<std::string> actions;
    int batch_step_count;
    int batch_size;

protected:
    //G4MultiFunctionalDetector *mfd;
    std::vector<G4LogicalVolume *> logicalVolumes;
};

#endif // GateVActor_h
