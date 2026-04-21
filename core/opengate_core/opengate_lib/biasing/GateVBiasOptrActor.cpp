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
  // SteppingAction may kill when the weight is too low (we leave this to
  // subclasses) fActions.insert("SteppingAction");
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
  if (G4EmParameters::Instance()->GeneralProcessActive()) {
    Fatal("GeneralGammaProcess is active. Biasing can *not* work for "
          "GateVBiasOptrActor");
  }
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

bool GateVBiasOptrActor::IsInExcludedVolumeAcrossAllWorlds(
    const G4Track *track) const {

  // Fast exit
  if (fExcludeVolumes.empty())
    return false;

  // Access thread-local cache
  threadLocalCache_t &l = fThreadLocalCache.Get();

  // Lazy cache: resolve volume names -> LV pointers + Daughters
  if (!l.fIsVolumePointersCached) {

    // Recursive lambda to add a volume and all its nested daughters
    std::function<void(const G4LogicalVolume *)> addWithDaughters =
        [&](const G4LogicalVolume *lv) {
          if (!lv)
            return;

          // Prevent duplicates (and infinite loops in case of weird geometry
          // graphs)
          if (std::find(l.fExcludedVolumePointers.begin(),
                        l.fExcludedVolumePointers.end(),
                        lv) == l.fExcludedVolumePointers.end()) {
            l.fExcludedVolumePointers.push_back(lv);
          }

          // Recursively add all daughters
          for (size_t i = 0; i < lv->GetNoDaughters(); ++i) {
            const G4LogicalVolume *daughterLV =
                lv->GetDaughter(i)->GetLogicalVolume();
            addWithDaughters(daughterLV);
          }
        };

    for (const auto &name : fExcludeVolumes) {
      const G4LogicalVolume *lv =
          G4LogicalVolumeStore::GetInstance()->GetVolume(name, false);
      if (lv) {
        addWithDaughters(lv);
      } else {
        G4Exception(
            "GateVBiasOptrActor", "MissingExcludedVolume", JustWarning,
            ("exclude_volumes: LV not found in store: " + name).c_str());
      }
    }
    l.fIsVolumePointersCached = true;
  }

  if (l.fExcludedVolumePointers.empty())
    return false;

  // Parallel world navigator query.
  G4TransportationManager *transport =
      G4TransportationManager::GetTransportationManager();
  const int numNav = transport->GetNoActiveNavigators();

  if (numNav <= 1) {
    return false;
  }

  const auto navIt = transport->GetActiveNavigatorsIterator();
  const G4ThreeVector &pos = track->GetPosition();

  // We MUST use the direction to correctly resolve boundary surfaces!
  const G4ThreeVector dir = track->GetMomentumDirection();

  // Index 0 is the mass world — start from 1
  for (int i = 1; i < numNav; ++i) {
    G4Navigator *realNav = *(navIt + i);
    if (!realNav)
      continue;

    // Use a stateless temporary navigator to avoid BIAS.GEN.02 state mismatches
    /*
     (1) realNav->CreateTouchableHistoryHandle() — reads the parallel
    navigator's internal state, which is only updated by G4CoupledTransportation
    at the end of each step. When ProposeOccurence is called (beginning of
    step), it reflects the previous step's position — one step behind.

    (2) realNav->LocateGlobalPointAndSetup(...) — calling this on the real
    parallel navigator corrupts G4CoupledTransportation's internal geometry
    state, causing navigation errors downstream.
     */
    l.fTmpNav.SetWorldVolume(realNav->GetWorldVolume());

    // Locate the point purely mathematically.
    // false (3rd arg) = search from root
    // false (4th arg) = do NOT ignore direction (solves boundary ties)
    const G4VPhysicalVolume *pv =
        l.fTmpNav.LocateGlobalPointAndSetup(pos, &dir, false, false);

    if (!pv)
      continue;

    // If it's just the empty world volume, skip it
    if (pv == realNav->GetWorldVolume())
      continue;

    const G4LogicalVolume *lv = pv->GetLogicalVolume();
    if (!lv)
      continue;

    // Pointer comparison against cached excluded LV list
    if (std::find(l.fExcludedVolumePointers.begin(),
                  l.fExcludedVolumePointers.end(),
                  lv) != l.fExcludedVolumePointers.end()) {
      return true;
    }
  }

  return false;
}