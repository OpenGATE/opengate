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
#include "GateVSource.h"
#include <pybind11/stl.h>

#include "GateGammaEmissionModel.h"

namespace py = pybind11;

class GatePositroniumSource : public GateVSource {

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

  double PrepareNextTime(double current_simulation_time) override;

  void PrepareNextRun() override;

  void GeneratePrimaries(G4Event *event, double time) override;


protected:
  unsigned long fNumberOfGeneratedEvents;

  // thread local structure
  struct threadLocalGenericSource {
    GateSingleParticleSource *fSPS = nullptr;
    GateAcceptanceAngleTesterManager *fAAManager = nullptr;
    bool fInitConfine = false;
    bool fInitGenericIon = false;
    double fEffectiveEventTime = -1;
    unsigned long fCurrentSkippedEvents = 0;
    unsigned long fCurrentZeroEvents = 0;
  };
  G4Cache<threadLocalGenericSource> fThreadLocalDataGenericSource;

  threadLocalGenericSource &GetThreadLocalDataGenericSource();

  virtual void CreateSPS();

  //virtual void InitializePosition(py::dict user_info);

protected:
  std::unique_ptr<GateGammaEmissionModel> pModel;
  ModelKind fModelKind = ModelKind::NotDefined;

};

#endif // GatePositroniumSource_h
