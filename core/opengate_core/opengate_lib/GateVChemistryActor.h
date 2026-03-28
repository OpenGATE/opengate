/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVChemistryActor_h
#define GateVChemistryActor_h

#include "GateVActor.h"

class GateVChemistryActor : public GateVActor {

public:
  explicit GateVChemistryActor(py::dict &user_info, bool MT_ready = false);

  ~GateVChemistryActor() override = default;

  void InitializeUserInfo(py::dict &user_info) override;

  // Called from G4ITTrackingInteractivity::StartTracking() for each chemistry track.
  virtual void StartChemistryTracking(G4Track *track);

  // Called from G4ITTrackingInteractivity::EndTracking() for each chemistry track.
  virtual void EndChemistryTracking(G4Track * /*track*/) {}

  // Called from G4UserTimeStepAction::StartProcessing() when the chemistry scheduler starts.
  virtual void StartProcessing() {}

  // Called from G4UserTimeStepAction::UserPreTimeStepAction() before each chemistry time step.
  virtual void UserPreTimeStepAction() {}

  // Called from G4UserTimeStepAction::UserPostTimeStepAction() after each chemistry time step.
  virtual void UserPostTimeStepAction() {}

  // Called from G4UserTimeStepAction::UserReactionAction() for each chemistry reaction.
  virtual void UserReactionAction(const G4Track & /*trackA*/,
                                  const G4Track & /*trackB*/,
                                  const std::vector<G4Track *> *
                                  /*products*/) {}

  // Called from G4UserTimeStepAction::EndProcessing() when the chemistry scheduler ends.
  virtual void EndProcessing() {}

protected:
  bool IsChemistryTrackInsideAttachedVolume(const G4Track *track) const;

  bool fConfineChemistryToVolume{false};
};

#endif // GateVChemistryActor_h
