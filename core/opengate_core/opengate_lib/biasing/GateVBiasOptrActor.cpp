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
    std::vector<const G4LogicalVolume *> &cache,
    const std::string &callerName) const {

  std::function<void(const G4LogicalVolume *)> addWithDaughters =
      [&](const G4LogicalVolume *lv) {
        if (!lv)
          return;
        // Prevent duplicates / infinite loops in unusual geometry graphs
        if (std::find(cache.begin(), cache.end(), lv) == cache.end()) {
          cache.push_back(lv);
          G4cout << "\t " << callerName << ": caching LV " << lv->GetName()
                 << G4endl;
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

bool GateVBiasOptrActor::IsInVolumeListAcrossAllWorlds(
    const G4Track *track,
    const std::vector<const G4LogicalVolume *> &cache) const {

  if (cache.empty())
    return false;

  const auto *massVol =
      track->GetVolume() ? track->GetVolume()->GetLogicalVolume() : nullptr;
  if (massVol &&
      std::find(cache.begin(), cache.end(), massVol) != cache.end()) {
    return true; // Found instantly in the mass world
  }

  G4TransportationManager *transport =
      G4TransportationManager::GetTransportationManager();
  const int numNav = transport->GetNoActiveNavigators();
  if (numNav <= 1)
    return false; // no parallel worlds

  const auto navIt = transport->GetActiveNavigatorsIterator();
  const G4ThreeVector &pos = track->GetPosition();
  const G4ThreeVector dir = track->GetMomentumDirection();

  // Retrieve the shared thread-local navigator
  G4Navigator &tmpNav = fThreadLocalCache.Get().fTmpNav;

  for (int i = 1; i < numNav; ++i) {
    G4Navigator *realNav = *(navIt + i);
    if (!realNav)
      continue;

    // Point tmpNav at this parallel world and do a pure mathematical
    // point-in-volume query. This does NOT touch the real navigator state.
    tmpNav.SetWorldVolume(realNav->GetWorldVolume());
    const G4VPhysicalVolume *pv =
        tmpNav.LocateGlobalPointAndSetup(pos, &dir, false, false);

    if (!pv)
      continue;
    if (pv == realNav->GetWorldVolume())
      continue; // parallel background

    const G4LogicalVolume *lv = pv->GetLogicalVolume();
    if (!lv)
      continue;

    if (std::find(cache.begin(), cache.end(), lv) != cache.end())
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

bool GateVBiasOptrActor::IsStepEnteringVolumeAcrossAllWorlds_NOT_USE(
    const G4Step *step,
    const std::vector<const G4LogicalVolume *> &volumes) const {

  if (!step || volumes.empty())
    return false;

  // ----------------------------------------------------------------
  // 1. FAST PATH: Mass Navigator Check (Boundary Trigger)
  // ----------------------------------------------------------------
  // If the step is limited by a mass geometry boundary, we check it instantly
  if (step->GetPostStepPoint()->GetStepStatus() == fGeomBoundary) {
    const auto *massVol = step->GetPostStepPoint()
                              ->GetTouchable()
                              ->GetVolume()
                              ->GetLogicalVolume();
    if (std::find(volumes.begin(), volumes.end(), massVol) != volumes.end()) {
      return true; // Hit a mass boundary and it's in the list
    }
  }

  // ----------------------------------------------------------------
  // 2. SLOW PATH: Parallel Navigators Check (Edge Detection)
  // ----------------------------------------------------------------
  G4TransportationManager *transport =
      G4TransportationManager::GetTransportationManager();
  const int numNav = transport->GetNoActiveNavigators();

  if (numNav <= 1)
    return false; // No parallel worlds exist, skip the math

  // We detect "entering" by proving the particle was OUTSIDE the volume
  // at the PreStepPoint, and INSIDE the volume at the PostStepPoint.
  const G4ThreeVector &prePos = step->GetPreStepPoint()->GetPosition();
  const G4ThreeVector &postPos = step->GetPostStepPoint()->GetPosition();
  const G4ThreeVector &dir = step->GetTrack()->GetMomentumDirection();

  G4Navigator &tmpNav = fThreadLocalCache.Get().fTmpNav;
  const auto navIt = transport->GetActiveNavigatorsIterator();

  // Start at i=1 to explicitly skip the Mass Navigator (already handled)
  for (int i = 1; i < numNav; ++i) {
    G4Navigator *realNav = *(navIt + i);
    if (!realNav)
      continue;

    tmpNav.SetWorldVolume(realNav->GetWorldVolume());

    // A. Check the END of the step
    const G4VPhysicalVolume *postPV =
        tmpNav.LocateGlobalPointAndSetup(postPos, &dir, false, false);

    if (!postPV || postPV == realNav->GetWorldVolume())
      continue;

    const G4LogicalVolume *postLV = postPV->GetLogicalVolume();

    // If the post-step volume is in our target list...
    if (std::find(volumes.begin(), volumes.end(), postLV) != volumes.end()) {

      // B. Check the START of the step
      const G4VPhysicalVolume *prePV =
          tmpNav.LocateGlobalPointAndSetup(prePos, &dir, false, false);
      const G4LogicalVolume *preLV =
          prePV ? prePV->GetLogicalVolume() : nullptr;

      // If the volumes are different, we just crossed the boundary!
      if (preLV != postLV) {
        return true;
      }
    }
  }

  return false;
}