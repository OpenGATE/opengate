/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateARFActor.h"
#include "G4Gamma.hh"
#include "G4RunManager.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

GateARFActor::GateARFActor(py::dict &user_info) : GateVActor(user_info, true) {
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("PreUserTrackingAction");
  fActions.insert("EndOfRunAction");
  fBatchSize = 0;
  fKeepNegativeSide = true;
}

void GateARFActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fBatchSize = DictGetInt(user_info, "batch_size");
  fKeepNegativeSide = DictGetBool(user_info, "flip_plane");
  fPlaneAxis = DictGetVecInt(user_info, "plane_axis");
}

void GateARFActor::SetARFFunction(ARFFunctionType &f) { fApply = f; }

void GateARFActor::BeginOfRunAction(const G4Run *run) {
  auto &l = fThreadLocalData.Get();
  l.fCurrentRunId = run->GetRunID();
  l.fCurrentNumberOfHits = 0;
}

void GateARFActor::EndOfRunAction(const G4Run * /*run*/) {
  auto &l = fThreadLocalData.Get();
  // When the run ends, we send the current remaining hits to the ARF
  if (l.fCurrentNumberOfHits > 0) {
    fApply(this);
    l.fEnergy.clear();
    l.fPositionX.clear();
    l.fPositionY.clear();
    // l.fPositionZ.clear();
    l.fDirectionX.clear();
    l.fDirectionY.clear();
    l.fDirectionZ.clear();
    l.fWeights.clear();
    l.fCurrentNumberOfHits = 0;
  }
}

void GateARFActor::PreUserTrackingAction(const G4Track *track) {
  GateVActor::PostUserTrackingAction(track);
  auto &l = fThreadLocalData.Get();
  l.fIsFirstInteraction = true;
}

void GateARFActor::SteppingAction(G4Step *step) {
  // First, only consider gammas
  if (step->GetTrack()->GetDefinition() != G4Gamma::GammaDefinition()) {
    return;
  }
  auto &l = fThreadLocalData.Get();
  if (!l.fIsFirstInteraction) {
    return;
  }

  // get direction and transform to local
  auto *pre = step->GetPreStepPoint();
  auto dir = pre->GetMomentumDirection();
  dir = pre->GetTouchable()->GetHistory()->GetTopTransform().TransformAxis(dir);
  dir = dir.unit();

  // which side of the plane ?
  if (!fKeepNegativeSide && dir[fPlaneAxis[2]] < 0)
    return;
  if (fKeepNegativeSide && dir[fPlaneAxis[2]] > 0)
    return;

  l.fCurrentNumberOfHits++;
  l.fDirectionX.push_back(dir[fPlaneAxis[0]]);
  l.fDirectionY.push_back(dir[fPlaneAxis[1]]);
  l.fDirectionZ.push_back(dir[fPlaneAxis[2]]);
  l.fWeights.push_back(pre->GetWeight());

  // get energy
  l.fEnergy.push_back(pre->GetKineticEnergy());

  // get position and transform to local
  auto pos =
      pre->GetTouchable()->GetHistory()->GetTopTransform().TransformPoint(
          pre->GetPosition());
  l.fPositionX.push_back(pos[fPlaneAxis[0]]);
  l.fPositionY.push_back(pos[fPlaneAxis[1]]);

  // trigger the "apply" (ARF) if the number of hits in the batch is reached
  if (l.fCurrentNumberOfHits >= fBatchSize) {
    fApply(this);
    l.fEnergy.clear();
    l.fPositionX.clear();
    l.fPositionY.clear();
    // l.fPositionZ.clear();
    l.fDirectionX.clear();
    l.fDirectionY.clear();
    l.fDirectionZ.clear();
    l.fWeights.clear();
    l.fCurrentNumberOfHits = 0;
  }

  l.fIsFirstInteraction = false;
}

int GateARFActor::GetCurrentNumberOfHits() const {
  return fThreadLocalData.Get().fCurrentNumberOfHits;
}

int GateARFActor::GetCurrentRunId() const {
  return fThreadLocalData.Get().fCurrentRunId;
}

std::vector<double> GateARFActor::GetEnergy() const {
  return fThreadLocalData.Get().fEnergy;
}

std::vector<double> GateARFActor::GetPositionX() const {
  return fThreadLocalData.Get().fPositionX;
}

std::vector<double> GateARFActor::GetPositionY() const {
  return fThreadLocalData.Get().fPositionY;
}

std::vector<double> GateARFActor::GetDirectionX() const {
  return fThreadLocalData.Get().fDirectionX;
}

std::vector<double> GateARFActor::GetDirectionY() const {
  return fThreadLocalData.Get().fDirectionY;
}

std::vector<double> GateARFActor::GetDirectionZ() const {
  return fThreadLocalData.Get().fDirectionZ;
}

std::vector<double> GateARFActor::GetWeights() const {
  return fThreadLocalData.Get().fWeights;
}
