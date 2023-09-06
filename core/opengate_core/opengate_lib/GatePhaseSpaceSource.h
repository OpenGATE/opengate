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
#include <pybind11/stl.h>

namespace py = pybind11;

class GatePhaseSpaceSource : public GateVSource {

public:
  // signature of the callback function in Python
  // that will generate particles (from phsp file)
  using ParticleGeneratorType = std::function<void(GatePhaseSpaceSource *)>;

  GatePhaseSpaceSource();

  ~GatePhaseSpaceSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void PrepareNextRun() override;

  double PrepareNextTime(double current_simulation_time) override;

  void GeneratePrimaries(G4Event *event,
                         double current_simulation_time) override;

  void GenerateOnePrimary(G4Event *event, double current_simulation_time);

  // void AddOnePrimaryVertex(G4Event *event, const G4ThreeVector &position,
  //                          const G4ThreeVector &momentum_direction,
  //                          double energy, double time, double w) const;

  void AddOnePrimaryVertex(G4Event *event, const G4ThreeVector &position,
                           const G4ThreeVector &momentum_direction,
                           double energy, double time, double w);

  void SetGeneratorFunction(ParticleGeneratorType &f);

  // virtual void SetGeneratorInfo(py::dict &user_info);

  void GenerateBatchOfParticles();

  G4ParticleDefinition *fParticleDefinition;
  G4ParticleTable *fParticleTable;
  double fCharge;
  double fMass;
  bool fGlobalFag;
  bool fUseParticleTypeFromFile;

  unsigned long fMaxN;
  long fNumberOfGeneratedEvents;
  size_t fCurrentBatchSize;

  std::vector<int> fPDGCode;
  std::vector<string> fParticleName;

  std::vector<double> fPositionX;
  std::vector<double> fPositionY;
  std::vector<double> fPositionZ;

  std::vector<double> fDirectionX;
  std::vector<double> fDirectionY;
  std::vector<double> fDirectionZ;

  std::vector<double> fEnergy;
  std::vector<double> fWeight;
  // std::vector<double> fTime;

  ParticleGeneratorType fGenerator;
  size_t fCurrentIndex;
};

#endif // GatePhaseSpaceSource_h
