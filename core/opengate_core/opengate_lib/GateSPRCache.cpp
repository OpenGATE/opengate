/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateSPRCache.h"

#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"

GateSPRCache::GateSPRCache() {}

GateSPRCache::~GateSPRCache() {}

void GateSPRCache::Initialize(G4Material *material, double constEnergy) {
  fMaterial = material;
  fConstantEnergy = constEnergy;
}

double GateSPRCache::FindOrCalculateSTR(const G4ParticleDefinition *particle,
                                        const G4Material *voxelMaterial) {
  if (particle == G4Gamma::Gamma())
    particle = G4Electron::Electron();
  std::string particleName = particle->GetParticleName();
  std::string materialName = voxelMaterial->GetName();
  CacheKey key{materialName, particleName};

  // check if the particle, material pair is already in the cache
  auto it = fSPRCache.find(key);
  if (it != fSPRCache.end()) {
    return it->second;
  }

  // if not, calulcate and store
  G4EmCalculator emcalc;
  double dedx_cut = DBL_MAX;
  double spr = 0.;
  auto dedxMaterial =
      emcalc.ComputeTotalDEDX(fConstantEnergy, particle, fMaterial, dedx_cut);
  auto dedxVoxel = emcalc.ComputeTotalDEDX(fConstantEnergy, particle,
                                           voxelMaterial, dedx_cut);
  if (dedxMaterial != 0 || dedxVoxel != 0) {
    spr = dedxMaterial / dedxVoxel;
  }

  fSPRCache[key] = spr;

  return spr;
}