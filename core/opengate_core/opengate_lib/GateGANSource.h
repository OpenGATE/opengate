/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateGANSource_h
#define GateGANSource_h

#include "GateGenericSource.h"
#include "GateSPSVoxelsPosDistribution.h"
#include "GateSingleParticleSource.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateGANSource : public GateGenericSource {

public:
  // signature of the callback function in Python
  // that will generate particles (from GAN)
  using ParticleGeneratorType = std::function<void(GateGANSource *)>;

  GateGANSource();

  ~GateGANSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void PrepareNextRun() override;

  void GeneratePrimaries(G4Event *event,
                         double current_simulation_time) override;

  void GenerateOnePrimary(G4Event *event, double current_simulation_time);

  void GenerateOnePrimaryWithAA(G4Event *event, double current_simulation_time);

  G4ThreeVector GeneratePrimariesPosition();
  G4ThreeVector GeneratePrimariesDirection();

  double GeneratePrimariesEnergy();
  double GeneratePrimariesTime(double current_simulation_time);
  double GeneratePrimariesWeight();

  void AddOnePrimaryVertex(G4Event *event, const G4ThreeVector &position,
                           const G4ThreeVector &momentum_direction,
                           double energy, double time, double w);

  void SetGeneratorFunction(ParticleGeneratorType &f);

  virtual void SetGeneratorInfo(py::dict &user_info);

  void GenerateBatchOfParticles();

  bool fPosition_is_set_by_GAN;
  bool fDirection_is_set_by_GAN;
  bool fEnergy_is_set_by_GAN;
  bool fTime_is_set_by_GAN;
  bool fWeight_is_set_by_GAN;

  size_t fCurrentBatchSize;

  std::vector<double> fPositionX;
  std::vector<double> fPositionY;
  std::vector<double> fPositionZ;

  std::vector<double> fDirectionX;
  std::vector<double> fDirectionY;
  std::vector<double> fDirectionZ;

  /// used to skip event with too low or too high energy
  double fEnergyMinThreshold;
  double fEnergyMaxThreshold;
  typedef GateAcceptanceAngleTesterManager::AAPolicyType SEPolicyType;
  SEPolicyType fSkipEnergyPolicy;

  bool fRelativeTiming;
  std::vector<double> fEnergy;
  std::vector<double> fWeight;
  std::vector<double> fTime;

  ParticleGeneratorType fGenerator;
  size_t fCurrentIndex;
  double fCharge;
  double fMass;
};

#endif // GateGANSource_h
