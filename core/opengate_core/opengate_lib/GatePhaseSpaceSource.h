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

  void SetGeneratorFunction(ParticleGeneratorType &f);

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

  void SetPDGCodeBatch(const py::array_t<std::int32_t> &fPDGCode);

  void SetEnergyBatch(const py::array_t<std::float_t> &fEnergy);

  void SetWeightBatch(const py::array_t<std::float_t> &fWeight);

  void SetPositionXBatch(const py::array_t<std::float_t> &fPositionX);

  void SetPositionYBatch(const py::array_t<std::float_t> &fPositionY);

  void SetPositionZBatch(const py::array_t<std::float_t> &fPositionZ);

  void SetDirectionXBatch(const py::array_t<std::float_t> &fDirectionX);

  void SetDirectionYBatch(const py::array_t<std::float_t> &fDirectionY);

  void SetDirectionZBatch(const py::array_t<std::float_t> &fDirectionZ);

protected:
  G4ParticleDefinition *fParticleDefinition = nullptr;

  bool fGenerateUntilNextPrimary = false;
  std::int32_t fPrimaryPDGCode = 0;
  std::float_t fPrimaryLowerEnergyThreshold = 0.0;

  ParticleGeneratorType fGenerator;
  size_t fCurrentIndex = 0;
  size_t fCurrentBatchSize = 0;

  std::int32_t *fPDGCode = nullptr;

  std::float_t *fPositionX = nullptr;
  std::float_t *fPositionY = nullptr;
  std::float_t *fPositionZ = nullptr;

  std::float_t *fDirectionX = nullptr;
  std::float_t *fDirectionY = nullptr;
  std::float_t *fDirectionZ = nullptr;

  std::float_t *fEnergy = nullptr;
  std::float_t *fWeight = nullptr;
};

#endif // GatePhaseSpaceSource_h
