/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateARFActor.h"
#include "G4RunManager.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

GateARFActor::GateARFActor(py::dict &user_info) : GateVActor(user_info, true) {
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("EndOfRunAction");
  // User option: batch size
  fBatchSize = DictGetInt(user_info, "batch_size");
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
    l.fDirectionX.clear();
    l.fDirectionY.clear();
    l.fCurrentNumberOfHits = 0;
  }
}

void GateARFActor::SteppingAction(G4Step *step) {
  auto &l = fThreadLocalData.Get();

  l.fCurrentNumberOfHits++;

  // get energy
  auto *pre = step->GetPreStepPoint();
  l.fEnergy.push_back(pre->GetKineticEnergy());

  // get position and transform to local
  auto pos =
      pre->GetTouchable()->GetHistory()->GetTopTransform().TransformPoint(
          pre->GetPosition());
  l.fPositionX.push_back(pos[0]);
  l.fPositionY.push_back(pos[1]);

  // get direction and transform to local
  auto dir = pre->GetMomentumDirection();
  dir = pre->GetTouchable()->GetHistory()->GetTopTransform().TransformAxis(dir);
  l.fDirectionX.push_back(dir[0]);
  l.fDirectionY.push_back(dir[1]);

  // trigger the "apply" (ARF) if the number of hits in the batch is reached
  if (l.fCurrentNumberOfHits >= fBatchSize) {
    fApply(this);
    l.fEnergy.clear();
    l.fPositionX.clear();
    l.fPositionY.clear();
    l.fDirectionX.clear();
    l.fDirectionY.clear();
    l.fCurrentNumberOfHits = 0;
  }
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
