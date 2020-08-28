/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamTestProtonSource_h
#define GamTestProtonSource_h

#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4ParticleGun.hh"

class GamTestProtonSource : public G4VUserPrimaryGeneratorAction {

public:

    GamTestProtonSource();

    virtual void GeneratePrimaries(G4Event *anEvent);

protected:
    G4ParticleGun *fParticleGun;
};

#endif // GamTestProtonSource
