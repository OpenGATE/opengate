/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateARFTrainingDatasetActor.h"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "GateActorManager.h"
#include "GateHelpersDict.h"
#include "GateHitsCollectionManager.h"
#include "GateTHitAttribute.h"

GateARFTrainingDatasetActor::GateARFTrainingDatasetActor(py::dict &user_info)
    : GateHitsCollectionActor(user_info) {
  // action
  fActions.insert("EndOfEventAction");
  // options
  fEnergyWindowActorName = DictGetStr(user_info, "energy_windows_actor");
  fARFHitsCollectionName = DictGetStr(user_info, "hits_collection_name");
  fARFHitsCollectionAttribute =
      DictGetStr(user_info, "hits_collection_attribute");
  fRussianRouletteValue = DictGetInt(user_info, "russian_roulette");
  if (fEnergyWindowActorName != "None")
    fScoreEnergyWindow = true;
  if (fARFHitsCollectionName != "None")
    fScoreDepositedEnergy = true;
  // init
  if (fScoreEnergyWindow) {
    fEnergyWindowsActor = dynamic_cast<GateHitsEnergyWindowsActor *>(
        GateActorManager::GetActor(fEnergyWindowActorName));
  }
  fRussianRouletteFactor = 1.0 / fRussianRouletteValue;
}

void GateARFTrainingDatasetActor::StartSimulationAction() {
  fHits = GateHitsCollectionManager::GetInstance()->NewHitsCollection(
      fHitsCollectionName);
  fHits->SetFilename(fOutputFilename);
  // create the hits collection
  fHits->StartInitialization();

  // create the attributes
  auto *att_e = new GateTHitAttribute<double>("E");
  auto *att_t = new GateTHitAttribute<double>("Theta");
  auto *att_p = new GateTHitAttribute<double>("Phi");
  fHits->InitializeHitAttribute(att_e);
  fHits->InitializeHitAttribute(att_t);
  fHits->InitializeHitAttribute(att_p);
  if (fScoreEnergyWindow) {
    auto *att_w = new GateTHitAttribute<double>("window");
    fHits->InitializeHitAttribute(att_w);
  }
  if (fScoreDepositedEnergy) {
    auto *att_edep = new GateTHitAttribute<double>("Edep");
    fHits->InitializeHitAttribute(att_edep);
  }
  fHits->FinishInitialization();
  fHits->InitializeRootTupleForMaster();

  // prepare the pointers to the attributes
  fAtt_E = fHits->GetHitAttribute("E");
  fAtt_Theta = fHits->GetHitAttribute("Theta");
  fAtt_Phi = fHits->GetHitAttribute("Phi");
  if (fScoreEnergyWindow)
    fAtt_W = fHits->GetHitAttribute("window");
  if (fScoreDepositedEnergy)
    fAtt_Edep = fHits->GetHitAttribute("Edep");
}

void GateARFTrainingDatasetActor::BeginOfEventAction(const G4Event *event) {
  GateHitsCollectionActor::BeginOfEventAction(event);
  // some events will never reach the detector,
  // we used fE == -1 to detect and ignore them
  fThreadLocalData.Get().fE = -1;
}

void GateARFTrainingDatasetActor::SteppingAction(G4Step *step) {
  auto &l = fThreadLocalData.Get();
  /*
   A gamma reach the detector, we store the energy and direction.
   It will be used at the end of the event, once the digitization process end.
   */
  // Get all values, will be filled at end of events.
  auto *pre = step->GetPreStepPoint();
  l.fE = pre->GetKineticEnergy();
  const auto *theTouchable = step->GetPreStepPoint()->GetTouchable();
  auto dir = pre->GetMomentumDirection();
  dir = theTouchable->GetHistory()->GetTopTransform().TransformAxis(dir);
  dir = dir.unit();
  l.fTheta = acos(dir.y()) / CLHEP::degree;
  l.fPhi = acos(dir.x()) / CLHEP::degree;
}

void GateARFTrainingDatasetActor::EndOfEventAction(const G4Event * /*event*/) {
  auto &l = fThreadLocalData.Get();
  // If the event did not reach the detector (in the stepping action), we ignore
  // it.
  if (l.fE == -1)
    return;
  /*
   Now the digitization process is terminated, we can retrieve the associated
   Energy Window id. We retrieve the window id, id=-1 means "outside" WARNING:
   in previous gate versions, outside id was equal to zero, so we stay
   compatible and offset everything by one.
  */

  if (fScoreEnergyWindow) {
    int w = fEnergyWindowsActor->GetLastEnergyWindowId() + 1;
    // If this is outside, we apply the russian roulette
    if (w == 0) {
      auto x = G4UniformRand();
      if (x > fRussianRouletteFactor)
        return;
    }
    fAtt_W->FillDValue(w);
  }

  if (fScoreDepositedEnergy) {
    auto hc = GateHitsCollectionManager::GetInstance()->GetHitsCollection(
        fARFHitsCollectionName);
    auto beginIndex = hc->GetBeginOfEventIndex();
    auto n = hc->GetSize() - beginIndex;
    double edep;
    if (n <= 0) {
      auto x = G4UniformRand();
      if (x > fRussianRouletteFactor)
        return;
      edep = -1.;
    } else {
      auto att = hc->GetHitAttribute(fARFHitsCollectionAttribute);
      edep = att->GetDValues().back();
    }
    fAtt_Edep->FillDValue(edep);
  }

  // Fill E, theta, phi and w
  fAtt_E->FillDValue(l.fE);
  fAtt_Theta->FillDValue(l.fTheta);
  fAtt_Phi->FillDValue(l.fPhi);
}

void GateARFTrainingDatasetActor::EndSimulationAction() {
  GateHitsCollectionActor::EndSimulationAction();
}
