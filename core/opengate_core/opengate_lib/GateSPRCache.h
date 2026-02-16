/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSPRCache_h
#define GateSPRCache_h

#include <functional>
#include <string>
#include <unordered_map>

#include "G4Material.hh"
#include "G4ParticleDefinition.hh"

struct CacheKey {
  std::string material;
  std::string particle;

  bool operator==(const CacheKey &other) const {
    return material == other.material && particle == other.particle;
  }
};

// Custom hash, needed to be able to correctly use "find" on unordered_map
struct CacheKeyHash {
  std::size_t operator()(const CacheKey &k) const {
    std::hash<std::string> hasher{};
    size_t h1 = hasher(k.material);
    size_t h2 = hasher(k.particle);
    return h1 ^ (h2 << 1); // simple combination
  }
};

class GateSPRCache {
public:
  GateSPRCache();
  ~GateSPRCache();

  /**
   * @brief Cache to calculate and store the SPR, assumingit is constant with
   * energy
   * @param material is the G4Material used to calculate the stopping power
   * ratio denominator
   * @param constEnergy is the constant energy value used for the SPR
   * calculation
   */
  void Initialize(G4Material *material, double constEnergy);

  /**
   * @brief Returns the ratio of the stopping power of p in material m and of p
   * in fMaterial
   * @param p is the particle interacting with the medium
   * @param m is the material used to calculate the stopping power of p
   * @retval SPR of m,m0
   */
  double FindOrCalculateSTR(const G4ParticleDefinition *p, const G4Material *m);

private:
  G4Material *fMaterial;
  double fConstantEnergy;
  std::unordered_map<CacheKey, double, CacheKeyHash> fSPRCache;
};

#endif // GateSPRCache_h