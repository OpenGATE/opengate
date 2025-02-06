/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVActor.h"

#include <G4LogicalVolumeStore.hh>

#include "G4SDManager.hh"
#include "GateActorManager.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateMultiFunctionalDetector.h"
#include "GateSourceManager.h"

GateVActor::GateVActor(py::dict &user_info, bool MT_ready)
    : G4VPrimitiveScorer(DictGetStr(user_info, "name")) {
  // register this actor to the global list of actors
  fMultiThreadReady = MT_ready;
  fOperatorIsAnd = true;
  fSourceManager = nullptr;
  fWriteToDisk = false;
}

GateVActor::~GateVActor() = default;

void GateVActor::InitializeCpp() {
  GateActorManager::AddActor(this);
  // Complain if the actor is not (yet) ready for multi-threading
  if (!fMultiThreadReady && G4Threading::IsMultithreadedApplication()) {
    std::ostringstream oss;
    oss << "Sorry, the actor '" << GetName()
        << "' cannot (yet) be used in multi-threads mode. ";
    Fatal(oss.str());
  }
};

void GateVActor::SetMotherAttachedToVolumeName(
    std::string attachedToVolumeName) {
  fAttachedToVolumeMotherName = attachedToVolumeName;
}

void GateVActor::InitializeUserInfo(py::dict &user_info) {
  fAttachedToVolumeName = DictGetStr(user_info, "attached_to");
  // fAttachedToVolumeMotherName = DictGetStr(user_info, "mother_attached_to");
  auto op = DictGetStr(user_info, "filters_boolean_operator");
  if (op == "and") {
    fOperatorIsAnd = true;
  } else {
    fOperatorIsAnd = false;
  }
  DDD(fAttachedToVolumeMotherName);
}

void GateVActor::AddActorOutputInfo(const std::string &outputName) {
  ActorOutputInfo_t aInfo;
  aInfo.outputName = outputName;
  fActorOutputInfos[outputName] = aInfo;
}

void GateVActor::SetOutputPath(const std::string &outputName,
                               const std::string &outputPath) {
  fActorOutputInfos[outputName].outputPath = outputPath;
}

std::string GateVActor::GetOutputPath(std::string outputName) const {
  try {
    ActorOutputInfo_t aInfo;
    aInfo = fActorOutputInfos.at(outputName);
    return aInfo.outputPath;
  } catch (std::out_of_range &) {
    std::ostringstream msg;
    msg << "(GetOutputPath) No actor output with the name " << outputName
        << " exists, attached to " << fAttachedToVolumeName << " " << GetName();
    Fatal(msg.str());
  }
  return ""; // to avoid warning
}

void GateVActor::SetWriteToDisk(const std::string &outputName,
                                const bool writeToDisk) {
  fActorOutputInfos[outputName].writeToDisk = writeToDisk;
}

bool GateVActor::GetWriteToDisk(std::string outputName) const {
  try {
    ActorOutputInfo_t aInfo;
    aInfo = fActorOutputInfos.at(outputName);
    return aInfo.writeToDisk;
  } catch (std::out_of_range &) {
    std::ostringstream msg;
    msg << "(GetWriteToDisk) No actor output with the name " << outputName
        << " exists exists in actor " << GetName() << " attached to "
        << fAttachedToVolumeName << ".";
    Fatal(msg.str());
  }
  return ""; // to avoid warning
}

void GateVActor::AddActions(std::set<std::string> &actions) {
  fActions.insert(actions.begin(), actions.end());
}

bool GateVActor::HasAction(const std::string &action) {
  return fActions.find(action) != fActions.end();
};

bool GateVActor::IsSensitiveDetector() { return HasAction("SteppingAction"); };

void GateVActor::PreUserTrackingAction(const G4Track *track) {
  for (auto f : fFilters) {
    if (!f->Accept(track))
      return;
  }
}

void GateVActor::PostUserTrackingAction(const G4Track *track) {
  for (auto f : fFilters) {
    if (!f->Accept(track))
      return;
  }
}

G4bool GateVActor::ProcessHits(G4Step *step, G4TouchableHistory *) {
  /*
   In the G4 docs:

   "The second argument is a G4TouchableHistory object for the Readout geometry
   described in the next section. The second argument is NULL if Readout
   geometry is not assigned to this sensitive detector. In this method, one or
   more G4VHit objects should be constructed if the current step is meaningful
   for your detector."

   "The second argument of FillHits() method, i.e. G4TouchableHistory, is
   obsolete and not used. If user needs to define an artificial second geometry,
   use Parallel Geometries."

    => so we decide to simplify and remove "touchable" in the following.
   */

  // if the operator is AND, we perform the SteppingAction only if ALL filters
  // are true (If only one is false, we stop and return)
  if (fOperatorIsAnd) {
    for (auto f : fFilters) {
      if (!f->Accept(step))
        return true;
    }
    SteppingAction(step);
    return true;
  }
  // if the operator is OR, we accept as soon as one filter is OK
  for (auto f : fFilters) {
    if (f->Accept(step)) {
      SteppingAction(step);
      return true;
    }
  }
  return true;
}

void GateVActor::RegisterSD(G4LogicalVolume *lv) {
  // Look is a SD already exist for this LV
  auto currentSD = lv->GetSensitiveDetector();
  GateMultiFunctionalDetector *mfd;
  if (!currentSD) {
    // This is the first time a SD is set to this LV
    auto f = new GateMultiFunctionalDetector("mfd_" + lv->GetName());
    G4SDManager::GetSDMpointer()->AddNewDetector(f);
    lv->SetSensitiveDetector(f);
    mfd = f;
  } else {
    // A SD already exist, we reused it
    mfd = dynamic_cast<GateMultiFunctionalDetector *>(currentSD);
    for (auto i = 0; i < mfd->GetNumberOfPrimitives(); i++) {
      if (mfd->GetPrimitive(i)->GetName() == GetName()) {
        // In that case the actor is already registered, we skip to avoid
        // G4 exception. It happens when the LogVol has several PhysVol
        // (repeater)
        return;
      }
    }
  }
  // Register the actor to the GateMultiFunctionalDetector
  mfd->RegisterPrimitive(this);
}

void GateVActor::SetSourceManager(GateSourceManager *s) { fSourceManager = s; }

bool GateVActor::IsStepExitVolume(const G4Step *step) const {
  // Checking if the particle is exiting the volume is tricky.
  // We need to check if the post point is in the mother volume and if
  // it is at a boundary (or in the world)

  // If the post step is world boundary: exiting
  if (step->GetPostStepPoint()->GetStepStatus() == fWorldBoundary)
    return true;

  // If the post step is not on a boundary: not exiting
  if (step->GetPostStepPoint()->GetStepStatus() != fGeomBoundary)
    return false;

  // step->IsLastStepInVolume() cannot be used here, because we dont know if the
  // volume we are exiting is the fAttachedToVolume. When daughters boundaries
  // overlap fAttachedToVolume boundaries, post step gives the daughter.

  // if the post step is at boundary AND if it is in the mother volume: exiting
  auto *vol = step->GetPostStepPoint()->GetTouchable()->GetVolume();
  auto vol_name = vol->GetName();
  if (fAttachedToVolumeMotherName == "None") {
    Fatal("Cannot use IsStepExitVolume when fAttachedToVolumeMotherName is "
          "empty");
  }
  return vol_name == fAttachedToVolumeMotherName;
}