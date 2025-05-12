#ifndef OPENGATE_CORE_OPENGATE_LIB_GATEFILTERDATA_H
#define OPENGATE_CORE_OPENGATE_LIB_GATEFILTERDATA_H

#include <G4Step.hh>

namespace attr {

struct ParticleName;
struct PreKineticEnergy;

} // namespace attr

template <typename Attr> struct GetAttr;

template <> struct GetAttr<attr::ParticleName> {
  static std::string get(G4Step *step) {
    return step->GetTrack()->GetParticleDefinition()->GetParticleName();
  }
};

template <> struct GetAttr<attr::PreKineticEnergy> {
  static double get(G4Step *step) {
    return step->GetPreStepPoint()->GetKineticEnergy();
  }
};

#endif
