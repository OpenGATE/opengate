/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateITTrackingInteractivity_h
#define GateITTrackingInteractivity_h

#include "G4ITTrackingInteractivity.hh"
#include "GateVChemistryActor.h"

class GateITTrackingInteractivity : public G4ITTrackingInteractivity {

public:
  GateITTrackingInteractivity();

  ~GateITTrackingInteractivity() override = default;

  void RegisterActor(GateVChemistryActor *actor);

  void Initialize() override;
  void AppendStep(G4Track *track, G4Step *step) override;
  void StartTracking(G4Track *track) override;
  void EndTracking(G4Track *track) override;
  void Finalize() override;

protected:
  std::vector<GateVChemistryActor *> fInitializeTrackingActors;
  std::vector<GateVChemistryActor *> fAppendStepActors;
  std::vector<GateVChemistryActor *> fStartTrackingActors;
  std::vector<GateVChemistryActor *> fEndTrackingActors;
  std::vector<GateVChemistryActor *> fFinalizeTrackingActors;
};

#endif // GateITTrackingInteractivity_h
