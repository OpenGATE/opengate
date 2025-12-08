/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTreatmentPlanPBSource_h
#define GateTreatmentPlanPBSource_h

// CLHEP
#include "CLHEP/Random/RandGauss.h"
#include "CLHEP/Random/RandomEngine.h"
#include "Randomize.hh"

#include "GateSingleParticleSourcePencilBeam.h"
#include "GateVSource.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateTreatmentPlanPBSource : public GateVSource {

public:
  GateTreatmentPlanPBSource();
  ~GateTreatmentPlanPBSource() override;

  void InitializeUserInfo(py::dict &user_info) override;
  void GeneratePrimaries(G4Event *event, double time) override;
  double PrepareNextTime(double current_simulation_time,
                         double NumberOfGeneratedEvents) override;
  void PrepareNextRun() override;
  double CalcNextTime(double current_simulation_time) override;

  // unsigned long fNumberOfGeneratedEvents;
  py::list GetGeneratedPrimaries();

protected:
  // thread local structure
  struct threadLocalTPSource {
    GateSingleParticleSourcePencilBeam *fSPS_PB = nullptr;
    std::vector<int> fNbIonsToGenerate;
    std::vector<int> fNbGeneratedSpots;
    int fCurrentSpot = 0;
    int fPreviousSpot = -1;
    bool fInitGenericIon = false;
  };
  G4Cache<threadLocalTPSource> fThreadLocalDataTPSource;

  threadLocalTPSource &GetThreadLocalDataTPSource();

  // variables common to all spots
  CLHEP::HepRandomEngine *fEngine;
  CLHEP::RandGeneral *fDistriGeneral;
  G4String fParticleType;
  bool fSortedSpotGenerationFlag;

  // vectors collecting spot-specific variables
  double *fPDF;
  std::vector<double> fSpotWeight;
  std::vector<double> fSpotEnergy;
  std::vector<double> fSigmaEnergy;
  std::vector<std::vector<double>> fPhSpaceX;
  std::vector<std::vector<double>> fPhSpaceY;
  std::vector<G4ThreeVector> fSpotPosition;
  std::vector<G4RotationMatrix> fSpotRotation;

  // other variables
  int fTotalNumberOfSpots;
  int fA;    // A: Atomic Mass (nn + np +nlambda)
  int fZ;    // Z: Atomic Number
  double fE; // E: Excitation energy
  G4ParticleDefinition *fParticleDefinition;

  // functions
  void FindNextSpot();
  void ConfigureSingleSpot();
  void UpdateEnergySPS(double energy, double sigma);
  void UpdatePositionSPS(const G4ThreeVector &localTransl,
                         const G4RotationMatrix &localRot);
  void InitializeParticle(py::dict &user_info);
  void InitializeIon(py::dict &user_info);
  void InitRandomEngine();
  void InitNbPrimariesVec();
};
#endif // GateTreatmentPlanPBSource_h
