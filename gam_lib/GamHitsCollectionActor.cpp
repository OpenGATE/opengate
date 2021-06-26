/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <vector>
#include <iostream>
#include "G4VProcess.hh"
#include "G4GenericAnalysisManager.hh"
#include "G4RunManager.hh"
#include "GamHitsCollectionActor.h"
#include "GamDictHelpers.h"


G4Mutex GamHitsActorMutex = G4MUTEX_INITIALIZER; // FIXME

GamHitsCollectionActor::GamHitsCollectionActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndSimulationAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("PreUserTrackingAction");
    fActions.insert("EndOfEventAction");
    fActions.insert("SteppingAction");
    fOutputFilename = DictStr(user_info, "output");
}

GamHitsCollectionActor::~GamHitsCollectionActor() {
}

// Called when the simulation start
void GamHitsCollectionActor::StartSimulationAction() {

    GamVBranch::InitAvailableBranches();

    /*
     FIXME Later: dynamics list of hits + list of process
     */

    // Init fHits branches
    fHits.name = "Hits";
    fHits.AddBranch("TotalEnergyDeposit");
    fHits.AddBranch("LocalTime");
    fHits.AddBranch("KineticEnergy");
    fHits.AddBranch("PostPosition");
    fHits.AddBranch("VolumeName");
    DDD(fHits.Dump());

    // Init fSingles branches
    fSingles.name = "Singles";
    fSingles.AddBranch("VolumeName");
    fSingles.AddBranch("TotalEnergyDeposit");
    fSingles.AddBranch("KineticEnergy");
    fSingles.AddBranch("PostPosition");
    fSingles.AddBranch("LocalTime");
    DDD(fSingles.Dump());

    // output hits collections
    fScatter.name = "Scatter";
    fPeak.name = "Peak";
    for (auto b:fSingles.fBranches) { // FIXME as a function (CopyBranches)
        fScatter.AddBranch(b->fBranchName);
        fPeak.AddBranch(b->fBranchName);
    }

    DDD(fScatter.Dump());
    DDD(fPeak.Dump());

    // Init processing modules
    fTakeEnergyCentroid.fHits = &fHits;
    fTakeEnergyCentroid.fSingles = &fSingles;
    fTakeEnergyCentroid.fIndex = 0;

    fEnergyWindow.fSingles = &fSingles;
    fEnergyWindow.fWindow = &fPeak;
    fEnergyWindow.Emin = 126.45 * CLHEP::keV;
    fEnergyWindow.Emax = 154.55 * CLHEP::keV;
}

// Called when the simulation end
void GamHitsCollectionActor::EndSimulationAction() {
    DDD("EndSimulationAction");
}

// Called every time a Run starts
void GamHitsCollectionActor::BeginOfRunAction(const G4Run * /*run*/) {
    DDD("Begin of Run");
}

// Called every time a Run ends
void GamHitsCollectionActor::EndOfRunAction(const G4Run * /*run*/) {
    DDD("end of run");

    DDD(fHits.Dump());
    DDD(fSingles.Dump());

    fHits.WriteToRoot("hits.root");
    fSingles.WriteToRoot("singles.root");
    DDD("end write root");

    fEnergyWindow.DoIt();
    DDD("end win doit");

    DDD(fScatter.Dump());
    DDD(fPeak.Dump());

    fSingles.WriteToRoot("peak.root");
}

void GamHitsCollectionActor::BeginOfEventAction(const G4Event */*event*/) {

}

void GamHitsCollectionActor::EndOfEventAction(const G4Event *) {
    DDD("End of Event");
    /*
    auto keb = dynamic_cast<GamBranch<double> *>(fHits.fBranches[0]);
    auto n = keb->values.size();
    DDD(n);
    for (auto i = fPreviousIndex; i < n; i++) {
        DDD(keb->values[i]);
    }
    fPreviousIndex = n;
*/
    fTakeEnergyCentroid.DoIt();
    //auto E = dynamic_cast<GamKineticEnergyBranch *>(fSingles.fBranches[0]);
    ///DDD(fHits.GetBranch(""))
    //auto E = fSingles.fBranches[0]->GetAsDoubleBranch();
    //DDD(E->values.back());
}

// Called every time a Track starts
void GamHitsCollectionActor::PreUserTrackingAction(const G4Track *track) {

}

// Called every time a batch of step must be processed
void GamHitsCollectionActor::SteppingAction(G4Step *step, G4TouchableHistory *touchable) {
    fHits.FillStep(step, touchable);
}
