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

  void StartTracking(G4Track *track) override;
  void EndTracking(G4Track *track) override;

protected:
  std::vector<GateVChemistryActor *> fStartTrackingActors;
  std::vector<GateVChemistryActor *> fEndTrackingActors;
};

#endif // GateITTrackingInteractivity_h
