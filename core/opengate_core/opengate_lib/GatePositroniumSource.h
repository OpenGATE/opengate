/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GatePositroniumSource_h
#define GatePositroniumSource_h

#include "GateAcceptanceAngleTesterManager.h"
#include "GateSingleParticleSource.h"
#include "GateGenericSource.h"
#include <pybind11/stl.h>

#include "GateGammaEmissionModel.h"
#include "GatePositroniumDecayModel.h"

namespace py = pybind11;

class GatePositroniumSource : public GateGenericSource {

public:
  enum class ModelKind {
    NotDefined,
    ParaPositronium,
    OrthoPositronium,
    Positronium
  };

public:

  GatePositroniumSource();

  ~GatePositroniumSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void GeneratePrimaries(G4Event *event, double time) override;


protected:
  unsigned long fNumberOfGeneratedEvents;

  std::vector<PositroniumDecayKind> ParsePositroniumDecayKind(const std::vector<string> & decayKindsStr);

protected:
  std::unique_ptr<GateGammaEmissionModel> pModel;
  ModelKind fModelKind = ModelKind::NotDefined;

};

#endif // GatePositroniumSource_h
