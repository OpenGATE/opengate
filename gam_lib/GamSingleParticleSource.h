/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSingleParticleSource_h
#define GamSingleParticleSource_h

#include "G4SingleParticleSource_modified.h"
#include "GamSPSEneDistribution.h"

/*
 * WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
 * WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING

 The file G4SingleParticleSource_modified is copied from G4SingleParticleSource
 This is temporary -> instead, ask for modification in G4:
 - make eneGenerator public or accessible
 - make G4SPSEneDistribution->GenerateOne virtual

 Then, use GamSingleParticle source instead.

*/

class GamSingleParticleSource : public G4SingleParticleSource_modified {

public:

};

#endif // GamSingleParticleSource_h
