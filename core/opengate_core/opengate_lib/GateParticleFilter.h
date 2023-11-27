/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateParticleFilter_h
#define GateParticleFilter_h

#include "GateVFilter.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateParticleFilter : public GateVFilter {

public:
  GateParticleFilter() : GateVFilter() {}

  void Initialize(py::dict &user_info) override;

  // To avoid gcc -Woverloaded-virtual
  // https://stackoverflow.com/questions/9995421/gcc-woverloaded-virtual-warnings
  using GateVFilter::Accept;

  bool Accept(const G4Track *track) const override;

  bool Accept(G4Step *step) const override;

  G4String fParticleName;
  std::string fPolicy;
};

#endif // GateParticleFilter_h
