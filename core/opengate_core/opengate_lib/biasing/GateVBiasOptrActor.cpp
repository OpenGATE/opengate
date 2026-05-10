/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVBiasOptrActor.h"
#include "../GateHelpers.h"
#include "../GateHelpersDict.h"
#include "G4EmParameters.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4Navigator.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4RunManager.hh"
#include "G4TransportationManager.hh"
#include <functional> // Added for recursive lambda
#include <vnl_matrix.h>

GateVBiasOptrActor::GateVBiasOptrActor(const std::string &name,
                                       py::dict &user_info, const bool MT_ready)
    : G4VBiasingOperator(name), GateVActor(user_info, MT_ready) {
  // It seems that it is necessary in MT (see PreUserTrackingAction)
  fActions.insert("PreUserTrackingAction");
  fWeightCutoff = std::numeric_limits<double>::min(); // around 2.22507e-308
  fEnergyCutoff = 0;
}

GateVBiasOptrActor::~GateVBiasOptrActor() {
  // Unsure if it is needed
  ClearOperators();
}

std::vector<G4VBiasingOperator *> &
GateVBiasOptrActor::GetNonConstBiasingOperators() {
  // WARNING PEGI 18: Don't look at it if you are sensitive and have a pure
  // heart.
  auto &operators = const_cast<std::vector<G4VBiasingOperator *> &>(
      G4VBiasingOperator::GetBiasingOperators());
  return operators;
}

void GateVBiasOptrActor::ClearOperators() {
  GetNonConstBiasingOperators().clear();
}

void GateVBiasOptrActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);

  // minimal weight check
  fWeightCutoff = DictGetDouble(user_info, "weight_cutoff");
  if (fWeightCutoff < 0) {
    fWeightCutoff = std::numeric_limits<double>::min(); // around 2.22507e-308
  }

  fExcludeVolumes = DictGetVecStr(user_info, "exclude_volumes");

  fEnergyCutoff = DictGetDouble(user_info, "energy_cutoff");
  if (fEnergyCutoff < 0) {
    fEnergyCutoff = 0;
  }
}

void GateVBiasOptrActor::Configure() {
  if (!G4Threading::IsMultithreadedApplication())
    ConfigureForWorker();
}

void GateVBiasOptrActor::ConfigureForWorker() {
  auto *biasedVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
  if (biasedVolume == nullptr) {
    Fatal("Cannot find biased volume: " + fAttachedToVolumeName + " in actor" +
          fActorName);
  }
  AttachAllLogicalDaughtersVolumes(biasedVolume);
}

void GateVBiasOptrActor::PreUserTrackingAction(const G4Track *track) {
  // WARNING this is needed in the MT mode (only),
  // otherwise, StartTracking is not called
  if (G4Threading::IsMultithreadedApplication()) {
    StartTracking(track);
  }
}

bool GateVBiasOptrActor::IsTrackValid(const G4Track *track) const {
  // Must be inferior or equal for cases when energy is zero or weight is zero
  if (track->GetKineticEnergy() <= fEnergyCutoff)
    return false;
  if (track->GetWeight() <= fWeightCutoff)
    return false;
  return true;
}

void GateVBiasOptrActor::AttachAllLogicalDaughtersVolumes(
    G4LogicalVolume *volume) {
  // Do not attach to ignored volumes
  const auto iter = std::find(fExcludeVolumes.begin(), fExcludeVolumes.end(),
                              volume->GetName());
  if (iter != fExcludeVolumes.end())
    return;

  // Attach to the volume
  AttachTo(volume);

  // Propagate to daughters
  // FIXME: set an option to not propagate to daughters ?
  for (auto i = 0; i < volume->GetNoDaughters(); i++) {
    G4LogicalVolume *logicalDaughtersVolume =
        volume->GetDaughter(i)->GetLogicalVolume();
    AttachAllLogicalDaughtersVolumes(logicalDaughtersVolume);
  }
}

void GateVBiasOptrActor::SteppingAction(G4Step *step) {
  // nothing
}

void GateVBiasOptrActor::BuildLVCache(
    const std::vector<std::string> &names,
    std::unordered_set<const G4LogicalVolume *> &cache,
    const std::string &callerName) const {

  std::function<void(const G4LogicalVolume *)> addWithDaughters =
      [&](const G4LogicalVolume *lv) {
        if (!lv)
          return;
        // Prevent duplicates / infinite loops in unusual geometry graphs
        if (cache.count(lv) == 0) {
          cache.insert(lv);
        }
        for (size_t i = 0; i < lv->GetNoDaughters(); ++i)
          addWithDaughters(lv->GetDaughter(i)->GetLogicalVolume());
      };

  for (const auto &name : names) {
    const G4LogicalVolume *lv =
        G4LogicalVolumeStore::GetInstance()->GetVolume(name, false);
    if (lv) {
      addWithDaughters(lv);
    } else {
      G4Exception("GateVBiasOptrActor", "MissingVolume", JustWarning,
                  (callerName + ": LV not found in store: " + name).c_str());
    }
  }
}

const G4LogicalVolume *
GateVBiasOptrActor::GetVolumeFromParallelNavigator(const G4ThreeVector &pos,
                                                   const G4ThreeVector &dir,
                                                   G4Navigator *realNav) const {

  if (!realNav)
    return nullptr;

  G4Navigator &tmpNav = fThreadLocalCache.Get().fTmpNav;
  tmpNav.SetWorldVolume(realNav->GetWorldVolume());

  // Locate the point purely mathematically
  const G4VPhysicalVolume *pv =
      tmpNav.LocateGlobalPointAndSetup(pos, &dir, false, false);

  if (!pv || pv == realNav->GetWorldVolume())
    return nullptr;

  return pv->GetLogicalVolume();
}

bool GateVBiasOptrActor::IsInVolumeListAcrossAllWorlds(
    const G4Track *track,
    const std::unordered_set<const G4LogicalVolume *> &cache) const {

  if (cache.empty())
    return false;

  // 1. Mass Navigator Fast Path
  const auto *massVol =
      track->GetVolume() ? track->GetVolume()->GetLogicalVolume() : nullptr;
  if (massVol && cache.count(massVol) > 0)
    return true;

  // 2. Parallel Navigators
  G4TransportationManager *transport =
      G4TransportationManager::GetTransportationManager();
  const int numNav = transport->GetNoActiveNavigators();
  if (numNav <= 1)
    return false;

  const auto navIt = transport->GetActiveNavigatorsIterator();
  const G4ThreeVector &pos = track->GetPosition();
  const G4ThreeVector dir = track->GetMomentumDirection();

  for (int i = 1; i < numNav; ++i) {
    // REUSE HELPER
    const G4LogicalVolume *lv =
        GetVolumeFromParallelNavigator(pos, dir, *(navIt + i));
    if (lv && cache.count(lv) > 0)
      return true;
  }
  return false;
}

bool GateVBiasOptrActor::IsInExcludedVolumeAcrossAllWorlds(
    const G4Track *track) const {

  if (fExcludeVolumes.empty())
    return false;

  threadLocalCache_t &l = fThreadLocalCache.Get();
  if (!l.fIsVolumePointersCached) {
    BuildLVCache(fExcludeVolumes, l.fExcludedVolumePointers, "exclude_volumes");
    l.fIsVolumePointersCached = true;
  }

  return IsInVolumeListAcrossAllWorlds(track, l.fExcludedVolumePointers);
}

bool GateVBiasOptrActor::IsStepEnteringVolumeAcrossAllWorlds(
    const G4Step *step,
    const std::unordered_set<const G4LogicalVolume *> &volumes) const {

  if (!step || volumes.empty())
    return false;

  // 1. Mass Navigator Fast Path (Boundary Trigger)
  if (step->GetPostStepPoint()->GetStepStatus() == fGeomBoundary) {
    const auto *massVol = step->GetPostStepPoint()
                              ->GetTouchable()
                              ->GetVolume()
                              ->GetLogicalVolume();
    if (volumes.count(massVol) > 0)
      return true;
  }

  // 2. Parallel Navigators Edge Detection
  G4TransportationManager *transport =
      G4TransportationManager::GetTransportationManager();
  const int numNav = transport->GetNoActiveNavigators();
  if (numNav <= 1)
    return false;

  const G4ThreeVector &prePos = step->GetPreStepPoint()->GetPosition();
  const G4ThreeVector &postPos = step->GetPostStepPoint()->GetPosition();
  const G4ThreeVector &dir = step->GetTrack()->GetMomentumDirection();
  const auto navIt = transport->GetActiveNavigatorsIterator();

  for (int i = 1; i < numNav; ++i) {
    G4Navigator *realNav = *(navIt + i);

    // REUSE HELPER FOR END OF STEP
    const G4LogicalVolume *postLV =
        GetVolumeFromParallelNavigator(postPos, dir, realNav);

    if (postLV && volumes.count(postLV) > 0) {
      // REUSE HELPER FOR START OF STEP
      const G4LogicalVolume *preLV =
          GetVolumeFromParallelNavigator(prePos, dir, realNav);

      if (preLV != postLV)
        return true;
    }
  }
  return false;
}