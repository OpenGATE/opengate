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

// #include "GateAcceptanceAngleTesterManager.h"
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
  double PrepareNextTime(double current_simulation_time) override;
  void PrepareNextRun() override;
  double CalcNextTime(double current_simulation_time);

  unsigned long fNumberOfGeneratedEvents;

protected:
  // variables common to all spots
  CLHEP::HepRandomEngine *engine;
  CLHEP::RandGeneral *mDistriGeneral;
  double fEffectiveEventTime;
  G4String mParticleType;
  bool mSortedSpotGenerationFlag;
  GateSingleParticleSourcePencilBeam *fSPS_PB;

  // vectors collecting spot-specific variables
  double *mPDF;
  std::vector<int> mNbIonsToGenerate;
  std::vector<double> mSpotWeight;
  std::vector<double> mSpotEnergy;
  std::vector<double> mSigmaEnergy;
  std::vector<std::vector<double>> mPhSpaceX;
  std::vector<std::vector<double>> mPhSpaceY;
  std::vector<G4ThreeVector> mSpotPosition;
  std::vector<G4RotationMatrix> mSpotRotation;

  // other variables
  int mCurrentSpot;
  int mPreviousSpot;
  int mTotalNumberOfSpots;
  bool fInitGenericIon;
  int fA;    // A: Atomic Mass (nn + np +nlambda)
  int fZ;    // Z: Atomic Number
  double fE; // E: Excitation energy
  G4ParticleDefinition *fParticleDefinition;

  // functions
  void FindNextSpot();
  void ConfigureSingleSpot();
  void UpdateEnergySPS(double energy, double sigma);
  void UpdatePositionSPS(G4ThreeVector localTransl, G4RotationMatrix localRot);
  void InitializeParticle(py::dict &user_info);
  void InitializeIon(py::dict &user_info);
  void InitRandomEngine();
  void InitNbPrimariesVec();
};
#endif // GateTreatmentPlanPBSource_h
