/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSingleParticleSourceWindowTurbo_h
#define GateSingleParticleSourceWindowTurbo_h

#include "GateSingleParticleSource.h"

class GateSingleParticleSourceWindowTurbo : public GateSingleParticleSource {
public:
  explicit GateSingleParticleSourceWindowTurbo(std::string mother_volume);
  ~GateSingleParticleSourceWindowTurbo() override;
  void GeneratePrimaryVertex(G4Event *event) override;
private:
  G4double GetSolidAngle(const G4ThreeVector &pos) const;
};

#endif // GateSingleParticleSourceWindowTurbo_h
