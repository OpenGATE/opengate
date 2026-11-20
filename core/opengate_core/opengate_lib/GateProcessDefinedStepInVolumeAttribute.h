/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateProcessDefinedStepInVolumeAttribute_h
#define GateProcessDefinedStepInVolumeAttribute_h

#include "GateVAuxiliaryAttribute.h"
#include <vector>

class G4LogicalVolume;
class G4Navigator;

/*
 * Count how often a given process defined a step of the current track while
 * the step was located in one of the configured volumes (or in any of their
 * daughters).
 *
 * Semantics:
 * - a step is counted when the process that limited THIS step (post-step
 *   point) is the configured one, and the pre-step point is in the volumes;
 * - the value returned for a step always includes that step, whether the
 *   getter is called before (sensitive detector, i.e. actors and filters) or
 *   after (stepping action) the counter has been updated;
 * - parallel worlds: a volume of a parallel world is found by locating the
 *   step in this world. A step located in a parallel-world volume that has a
 *   material (layered mass geometry) belongs to this volume and is not
 *   counted in the volumes of the mass world found at the same place;
 * - with propagate_from_parent_track, a secondary starts with the count of
 *   its parent including the step that created it.
 */
class GateProcessDefinedStepCounterTrackData
    : public GateIntegerCounterTrackData {
public:
  // step number (of the owning track) of the last step already counted
  int fLastCountedStepNumber{0};
};

class GateProcessDefinedStepInVolumeAttribute : public GateVAuxiliaryAttribute {
public:
  explicit GateProcessDefinedStepInVolumeAttribute(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  int GetIValue(const G4Step *step) const override;
  void SteppingAction(const G4Step *step) override;

protected:
  bool IsStepCounted(const G4Step *step) const;
  bool IsStepInVolumes(const G4Step *step) const;

  std::string fProcessName;
  std::vector<std::string> fVolumeNames;
  bool fPropagateFromParentTrack{false};

  // Logical volumes matching fVolumeNames, resolved once per thread
  struct threadLocalT {
    bool fResolved{false};
    std::vector<const G4LogicalVolume *> fLogicalVolumes;
    // One private navigator per parallel world (the navigators used for the
    // tracking are never touched)
    std::vector<G4Navigator *> fParallelWorldNavigators;
    ~threadLocalT();
  };
  void InitializeThreadLocalData(threadLocalT &l) const;
  bool IsLogicalVolumeSelected(const threadLocalT &l,
                               const G4LogicalVolume *lv) const;
  mutable G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateProcessDefinedStepInVolumeAttribute_h
