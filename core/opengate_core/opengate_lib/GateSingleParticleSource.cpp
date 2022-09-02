/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSingleParticleSource.h"
#include "G4Event.hh"
#include "G4PrimaryVertex.hh"
#include "G4RunManager.hh"
#include "GateHelpersDict.h"

#include "GateRandomMultiGauss.h"

GateSingleParticleSource::GateSingleParticleSource(
    std::string /*mother_volume*/) {
  fPositionGenerator = new GateSPSPosDistribution();
  fDirectionGenerator = new G4SPSAngDistribution();
  fEnergyGenerator = new GateSPSEneDistribution();

  // needed
  fBiasRndm = new G4SPSRandomGenerator();
  fPositionGenerator->SetBiasRndm(fBiasRndm);
  fDirectionGenerator->SetBiasRndm(fBiasRndm);
  fDirectionGenerator->SetPosDistribution(fPositionGenerator);
  fEnergyGenerator->SetBiasRndm(fBiasRndm);

  // Acceptance angle
  fAcceptanceAngleFlag = false;
  fAASkippedParticles = 0;
  fAALastRunId = -1;

  // For PBS
  mUXTheta = {0, 0};
  mUYPhi = {0, 0};
  mSXTheta = {0, 0, 0, 0};
  mSYPhi = {0, 0, 0, 0};
}

GateSingleParticleSource::~GateSingleParticleSource() {
  delete fPositionGenerator;
  delete fDirectionGenerator;
  delete fEnergyGenerator;
}

void GateSingleParticleSource::SetPosGenerator(GateSPSPosDistribution *pg) {
  fPositionGenerator = pg;
  fPositionGenerator->SetBiasRndm(fBiasRndm);
  fDirectionGenerator->SetPosDistribution(fPositionGenerator);
}

void GateSingleParticleSource::SetParticleDefinition(
    G4ParticleDefinition *def) {
  fParticleDefinition = def;
  fCharge = fParticleDefinition->GetPDGCharge();
  fMass = fParticleDefinition->GetPDGMass();
}

void GateSingleParticleSource::SetAcceptanceAngleParam(py::dict puser_info) {
  fAcceptanceAngleVolumeNames = DictGetVecStr(puser_info, "volumes");
  fAcceptanceAngleFlag = !fAcceptanceAngleVolumeNames.empty();
  // (we cannot use py::dict here as it is lost at the end of the function)
  fAcceptanceAngleParam = DictToMap(puser_info);
}

void GateSingleParticleSource::SetPBSourceParam(py::dict user_info) {
  auto x_param = DictGetVecDouble(user_info, "partPhSp_x");
  auto y_param = DictGetVecDouble(user_info, "partPhSp_y");

  sigmaX = x_param[0];
  sigmaY = y_param[0];
  thetaX = x_param[1];
  thetaY = y_param[1];
  epsilonX = x_param[2] / 3.14; // same formalism used in Gate-9
  epsilonY = y_param[2] / 3.14;
  convX = x_param[3];
  convY = y_param[3];
}

void GateSingleParticleSource::SetSourceRotTransl(G4ThreeVector t,
                                                  G4RotationMatrix r) {
  // set sorec rotation and translation
  source_transl = t;
  source_rot = r;
}

void GateSingleParticleSource::InitializeAcceptanceAngle() {
  // Create the testers (only the first time)
  if (fAATesters.empty()) {
    for (const auto &name : fAcceptanceAngleVolumeNames) {
      auto *t = new GateAcceptanceAngleTester(name, fAcceptanceAngleParam);
      fAATesters.push_back(t);
    }
  }

  // Update the transform (all runs!)
  for (auto *t : fAATesters)
    t->UpdateTransform();

  // store the ID of this Run
  fAALastRunId = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
}

bool GateSingleParticleSource::TestIfAcceptAngle(
    const G4ThreeVector &position, const G4ThreeVector &momentum_direction) {
  // If angle acceptance flag is enabled, we check if the particle is going to
  // intersect the given volume. If not, the energy is set to zero to ignore We
  // must initialize the angle every run because the associated volume may have
  // moved
  if (!fAcceptanceAngleFlag)
    return true;

  if (fAALastRunId !=
      G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID())
    InitializeAcceptanceAngle();

  bool shouldSkip = true;
  for (auto *tester : fAATesters) {
    bool accept = tester->TestIfAccept(position, momentum_direction);
    if (accept) {
      shouldSkip = false;
      continue;
    }
  }
  if (shouldSkip) {
    fAASkippedParticles++;
    return false;
  }
  return true;
}

void GateSingleParticleSource::GeneratePrimaryVertex(G4Event *event) {

  // (No mutex needed because variables (position, etc) are local)

  // position
  auto position = fPositionGenerator->VGenerateOne();

  // create a new vertex (time must have been set before with SetParticleTime)
  auto *vertex = new G4PrimaryVertex(position, particle_time);

  // direction
  auto momentum_direction = fDirectionGenerator->GenerateOne();

  // If angle acceptance, we check if the particle is going to intersect the
  // given volume. If not, the energy is set to zero to ignore
  double energy = 0;
  bool accept = TestIfAcceptAngle(position, momentum_direction);
  if (accept) {
    energy = fEnergyGenerator->VGenerateOne(fParticleDefinition);
  }

  // one single particle
  auto *particle = new G4PrimaryParticle(fParticleDefinition);
  particle->SetKineticEnergy(energy);
  particle->SetMass(fMass);
  particle->SetMomentumDirection(momentum_direction);
  particle->SetCharge(fCharge);

  // FIXME polarization
  // FIXME weight from eneGenerator + bias ? (should not be useful yet ?)

  // set vertex // FIXME change for back to back
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);
}

void GateSingleParticleSource::GeneratePrimaryVertexPB(G4Event *event) {

  if (!mIsInitialized) {

    //---------SOURCE PARAMETERS - CONTROL ----------------
    //   ## TO DO EARLIER ##

    //---------INITIALIZATION - START----------------------

    //==============================================================
    // X Phi Phase Space Ellipse

    delete mGaussian2DXTheta;

    PhaseSpace(sigmaX, thetaX, epsilonX, convX, mSXTheta);

    mGaussian2DXTheta = new GateRandomMultiGauss(mUXTheta, mSXTheta);

    //==============================================================
    // Y Phi Phase Space Ellipse

    delete mGaussian2DYPhi;

    PhaseSpace(sigmaY, thetaY, epsilonY, convY, mSYPhi);

    mGaussian2DYPhi = new GateRandomMultiGauss(mUYPhi, mSYPhi);

    //---------INITIALIZATION - END-----------------------
  }
  //=======================================================

  //-------- PARTICLE SAMPLING - START------------------
  G4ThreeVector position, Dir;

  // position/direction sampling
  std::vector<double> XTheta = mGaussian2DXTheta->Fire();
  std::vector<double> YPhi = mGaussian2DYPhi->Fire();

  position[2] = 0;         // Pz
  position[0] = XTheta[0]; // Px
  position[1] = YPhi[0];   // Py

  Dir[2] = 1;              // Dz
  Dir[0] = tan(XTheta[1]); // Dx
  Dir[1] = tan(YPhi[1]);   // Dy

  // move position according to mother volume
  position = source_rot * position + source_transl;

  // normalize (needed)
  Dir = Dir / Dir.mag();

  // move according to mother volume
  Dir = source_rot * Dir;

  // If angle acceptance, we check if the particle is going to intersect the
  // given volume.
  // If not, the energy is set to zero to ignore
  double energy = 0;
  bool accept =
      TestIfAcceptAngle(position, Dir); // Not sure if Dir or [px,py,pz]
  if (accept) {
    energy = fEnergyGenerator->VGenerateOne(fParticleDefinition);
  }

  //-------- PARTICLE SAMPLING - END------------------

  //=======================================================

  //-------- PARTICLE GENERATION - START------------------
  // create a new vertex (time must have been set before with SetParticleTime)
  auto *vertex = new G4PrimaryVertex(position, particle_time);

  auto *particle = new G4PrimaryParticle(fParticleDefinition);

  particle->SetKineticEnergy(energy);
  particle->SetMass(fMass);
  particle->SetMomentumDirection(Dir);
  particle->SetCharge(fCharge);

  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);

  //-------- PARTICLE GENERATION - END------------------
}

void GateSingleParticleSource::PhaseSpace(double sigma, double theta,
                                          double epsilon, double conv,
                                          std::vector<double> &symM) {

  // Notations & Calculations based on Transport code - Beam Phase Space
  // Notations - P35
  double alpha, beta, gamma;

  if (epsilon == 0) {
    std::cout << "Error Elipse area is 0 !!!" << std::endl;
  }
  beta = sigma * sigma / epsilon;
  gamma = theta * theta / epsilon;
  alpha = sqrt(beta * gamma - 1.);

  if (conv == 0) {
    alpha = -alpha;
  } // not convergent

  symM[0] = beta * epsilon;
  symM[1] = -alpha * epsilon;
  symM[2] = symM[1];
  symM[3] = gamma * epsilon;
}
