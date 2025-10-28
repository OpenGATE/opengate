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
  using ParticleGeneratorType = std::function<int(GatePhaseSpaceSource *, int)>;

  GatePhaseSpaceSource();

  ~GatePhaseSpaceSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void PrepareNextRun() override;

  void GeneratePrimaries(G4Event *event,
                         double current_simulation_time) override;

  void GenerateOnePrimary(G4Event *event, double current_simulation_time);

  void AddOnePrimaryVertex(G4Event *event, const G4ThreeVector &position,
                           const G4ThreeVector &momentum_direction,
                           double energy, double time, double w);

  void SetGeneratorFunction(ParticleGeneratorType &f) const;

  bool ParticleIsPrimary() const;

  G4ParticleMomentum GenerateRandomDirection();

  void GenerateBatchOfParticles();

  G4ParticleTable *fParticleTable;
  std::float_t fCharge;
  std::float_t fMass;
  bool fGlobalFag;
  bool fUseParticleTypeFromFile;
  bool fVerbose;
  G4bool fIsotropicMomentum;

  void SetPDGCodeBatch(const py::array_t<std::int32_t> &fPDGCode) const;

  void SetEnergyBatch(const py::array_t<std::float_t> &fEnergy) const;

  void SetWeightBatch(const py::array_t<std::float_t> &fWeight) const;

  void SetPositionXBatch(const py::array_t<std::float_t> &fPositionX) const;

  void SetPositionYBatch(const py::array_t<std::float_t> &fPositionY) const;

  void SetPositionZBatch(const py::array_t<std::float_t> &fPositionZ) const;

  void SetDirectionXBatch(const py::array_t<std::float_t> &fDirectionX) const;

  void SetDirectionYBatch(const py::array_t<std::float_t> &fDirectionY) const;

  void SetDirectionZBatch(const py::array_t<std::float_t> &fDirectionZ) const;

  // For MT, all threads local variables are gathered here
  struct threadLocalTPhsp {
    G4ParticleDefinition *fParticleDefinition;

    bool fGenerateUntilNextPrimary;
    std::int32_t fPrimaryPDGCode;
    std::float_t fPrimaryLowerEnergyThreshold;

    ParticleGeneratorType fGenerator;
    unsigned long fNumberOfGeneratedEvents;
    size_t fCurrentIndex;
    size_t fCurrentBatchSize;

    std::int32_t *fPDGCode;

    std::float_t *fPositionX;
    std::float_t *fPositionY;
    std::float_t *fPositionZ;

    std::float_t *fDirectionX;
    std::float_t *fDirectionY;
    std::float_t *fDirectionZ;

    std::float_t *fEnergy;
    std::float_t *fWeight;
    // double * fTime; // FIXME todo
  };
  G4Cache<threadLocalTPhsp> fThreadLocalDataPhsp;
};

#endif // GatePhaseSpaceSource_h
