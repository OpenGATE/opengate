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
  // signature of the callback function in Python that will generate particles
  // info
  using ParticleGeneratorType = std::function<void(GateGANSource *)>;

  GateGANSource();

  ~GateGANSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void PrepareNextRun() override;

  void GeneratePrimaries(G4Event *event,
                         double current_simulation_time) override;

  void GeneratePrimariesSingle(G4Event *event, double current_simulation_time);

  void GeneratePrimariesPair(G4Event *event, double current_simulation_time);

  void GeneratePrimariesAddOne(G4Event *event, G4ThreeVector position,
                               G4ThreeVector momentum_direction, double energy,
                               double time, double w);

  void SetGeneratorFunction(ParticleGeneratorType &f);

  void GetParticlesInformation();

  bool fIsPaired;

  std::vector<double> fPositionX;
  std::vector<double> fPositionY;
  std::vector<double> fPositionZ;

  std::vector<double> fDirectionX;
  std::vector<double> fDirectionY;
  std::vector<double> fDirectionZ;

  /// used to skip event with too low energy
  double fEnergyThreshold;
  GateAcceptanceAngleTesterManager::AAModeType fSkipEnergyEventMode;

  std::vector<double> fEnergy;
  bool fUseWeight;
  std::vector<double> fWeight;
  bool fUseTime;
  bool fUseTimeRelative;
  std::vector<double> fTime;

  // If pairs of particles
  std::vector<double> fPositionX2;
  std::vector<double> fPositionY2;
  std::vector<double> fPositionZ2;

  std::vector<double> fDirectionX2;
  std::vector<double> fDirectionY2;
  std::vector<double> fDirectionZ2;

  std::vector<double> fEnergy2;
  std::vector<double> fWeight2;
  std::vector<double> fTime2;

  ParticleGeneratorType fGenerator;
  size_t fCurrentIndex;
  double fCharge;
  double fMass;
};

#endif // GateGANSource_h
