/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GatePhaseSpaceSource_h
#define GatePhaseSpaceSource_h

#include "GateSPSVoxelsPosDistribution.h"
#include "GateSingleParticleSource.h"
#include "GateVSource.h"
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

class GatePhaseSpaceSource : public GateVSource {

public:
  // signature of the callback function in Python
  // that will generate particles (from phsp file)
  using ParticleGeneratorType = std::function<int(GatePhaseSpaceSource *)>;

  GatePhaseSpaceSource();

  ~GatePhaseSpaceSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void PrepareNextRun() override;

  double PrepareNextTime(double current_simulation_time) override;

  void GeneratePrimaries(G4Event *event,
                         double current_simulation_time) override;

  void GenerateOnePrimary(G4Event *event, double current_simulation_time);

  void AddOnePrimaryVertex(G4Event *event, const G4ThreeVector &position,
                           const G4ThreeVector &momentum_direction,
                           double energy, double time, double w);

  void SetGeneratorFunction(ParticleGeneratorType &f) const;

  void GenerateBatchOfParticles();

  G4ParticleDefinition *fParticleDefinition;
  G4ParticleTable *fParticleTable;
  double fCharge;
  double fMass;
  bool fGlobalFag;
  bool fUseParticleTypeFromFile;

  unsigned long fMaxN;

  void SetPDGCodeBatch(const py::array_t<std::int32_t> &fPDGCode) const;

  void SetEnergyBatch(const py::array_t<double> &fEnergy) const;

  void SetWeightBatch(const py::array_t<double> &fWeight) const;

  void SetPositionXBatch(const py::array_t<double> &fPositionX) const;

  void SetPositionYBatch(const py::array_t<double> &fPositionY) const;

  void SetPositionZBatch(const py::array_t<double> &fPositionZ) const;

  void SetDirectionXBatch(const py::array_t<double> &fDirectionX) const;

  void SetDirectionYBatch(const py::array_t<double> &fDirectionY) const;

  void SetDirectionZBatch(const py::array_t<double> &fDirectionZ) const;

  // For MT, all threads local variables are gathered here
  struct threadLocalTPhsp {

    ParticleGeneratorType fGenerator;
    unsigned long fNumberOfGeneratedEvents;
    size_t fCurrentIndex;
    size_t fCurrentBatchSize;

    int *fPDGCode;

    double *fPositionX;
    double *fPositionY;
    double *fPositionZ;

    double *fDirectionX;
    double *fDirectionY;
    double *fDirectionZ;

    double *fEnergy;
    double *fWeight;
    // double * fTime;
  };
  G4Cache<threadLocalTPhsp> fThreadLocalDataPhsp;
};

#endif // GatePhaseSpaceSource_h
