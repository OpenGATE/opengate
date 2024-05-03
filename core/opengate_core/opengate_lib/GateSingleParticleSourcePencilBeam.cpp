/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSingleParticleSourcePencilBeam.h"
#include "GateHelpersDict.h"

GateSingleParticleSourcePencilBeam::GateSingleParticleSourcePencilBeam(
    std::string motherVolume, std::string)
    : GateSingleParticleSource(motherVolume) {
  // Specific init for PBS
  mUXTheta = {0, 0};
  mUYPhi = {0, 0};
  mSXTheta = {0, 0, 0, 0};
  mSYPhi = {0, 0, 0, 0};
}

void GateSingleParticleSourcePencilBeam::SetPBSourceParam(
    std::vector<double> x_param, std::vector<double> y_param) {

  // pi = 3.14159265358979323846; # CLHEP value
  sigmaX = x_param[0];
  sigmaY = y_param[0];
  thetaX = x_param[1];
  thetaY = y_param[1];
  epsilonX =
      x_param[2] / 3.14159265358979323846; // same formalism used in Gate-9
  epsilonY = y_param[2] / 3.14159265358979323846;
  convX = x_param[3];
  convY = y_param[3];
}

void GateSingleParticleSourcePencilBeam::SetSourceRotTransl(
    G4ThreeVector t, G4RotationMatrix r) {
  // set source rotation and translation
  source_transl = t;
  source_rot = r;
}

void GateSingleParticleSourcePencilBeam::GeneratePrimaryVertex(G4Event *event) {
  if (!mIsInitialized) {

    //---------INITIALIZATION - START----------------------

    //==============================================================
    // Generates primary vertex: pos and dir are correlated and sampled from 2D
    // Gaussian x-direction
    delete mGaussian2DXTheta;
    // convert user input into a 2D Matrix, one sigma;
    // note: matrix mUX remains zero as initialized
    PhaseSpace(sigmaX, thetaX, epsilonX, convX, mSXTheta);
    mGaussian2DXTheta = new GateRandomMultiGauss(mUXTheta, mSXTheta);

    //==============================================================
    // y-direction
    delete mGaussian2DYPhi;
    PhaseSpace(sigmaY, thetaY, epsilonY, convY, mSYPhi);
    mGaussian2DYPhi = new GateRandomMultiGauss(mUYPhi, mSYPhi);

    //---------INITIALIZATION - END-----------------------
  }
  //=======================================================

  //-------- PARTICLE SAMPLING - START------------------
  G4ThreeVector position, direction;

  // position/direction sampling
  std::vector<double> XTheta = mGaussian2DXTheta->Fire();
  std::vector<double> YPhi = mGaussian2DYPhi->Fire();

  position[2] = 0;         // Pz
  position[0] = XTheta[0]; // Px
  position[1] = YPhi[0];   // Py

  direction[2] = 1;              // Dz
  direction[0] = tan(XTheta[1]); // Dx
  direction[1] = tan(YPhi[1]);   // Dy

  // move position according to mother volume
  position = source_rot * position + source_transl;

  // normalize (needed)
  direction = direction / direction.mag();

  // move according to mother volume
  direction = source_rot * direction;

  // (do not test for acceptance angle)
  auto energy = fEnergyGenerator->VGenerateOne(fParticleDefinition);

  //-------- PARTICLE SAMPLING - END------------------

  //=======================================================

  //-------- PARTICLE GENERATION - START------------------
  // create a new vertex (time must have been set before with SetParticleTime)
  auto *vertex = new G4PrimaryVertex(position, particle_time);

  auto *particle = new G4PrimaryParticle(fParticleDefinition);

  particle->SetKineticEnergy(energy);
  particle->SetMass(fMass);
  particle->SetMomentumDirection(direction);
  particle->SetCharge(fCharge);

  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);

  //-------- PARTICLE GENERATION - END------------------
}

void GateSingleParticleSourcePencilBeam::PhaseSpace(double sigma, double theta,
                                                    double epsilon, double conv,
                                                    std::vector<double> &symM) {
  // Notations & Calculations based on Transport code - Beam Phase Space
  // Notations - P35
  double alpha, beta, gamma;

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
