/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateFastY90Source.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include <G4ParticleTable.hh>
#include <G4PrimaryParticle.hh>
#include <G4PrimaryVertex.hh>
#include <G4RandomDirection.hh>
#include <G4SystemOfUnits.hh>
#include <Randomize.hh>
#include <cmath>

void GateFastY90Source::InitializeUserInfo(py::dict &user_info) {
  fKernel = GateFastY90Kernel(DictGetDouble(user_info, "min_brem_energy") /
                                  CLHEP::MeV,
                              DictGetDouble(user_info, "positron_probability"));
  fUseImage = !user_info["image"].is_none();
  GateGenericSource::InitializeUserInfo(user_info);
  fPositronDefinition = G4ParticleTable::GetParticleTable()->FindParticle("e+");
  if (fPositronDefinition == nullptr)
    Fatal("FastY90Source cannot find the positron particle definition.");

  // User activity and TAC values count decays. The native clock and event
  // estimates count transported emissions, exactly as GATE 9 GetNextTime.
  const auto yield = fKernel.GetTotalYield();
  fActivity *= yield;
  fInitialActivity *= yield;
  for (auto &activity : fTAC_Activities)
    activity *= yield;
}

void GateFastY90Source::InitializePosition(py::dict user_info) {
  if (!fUseImage)
    return GateGenericSource::InitializePosition(user_info);
  GateVoxelSource::InitializePosition(user_info);
  auto position = py::dict(user_info["position"]);
  fLocalTranslation = DictGetG4ThreeVector(position, "translation");
  auto rotation = DictGetMatrix(position, "rotation");
  fLocalRotation = ConvertToG4RotationMatrix(rotation);
}

void GateFastY90Source::PrepareNextRun() {
  if (fUseImage)
    GateVoxelSource::PrepareNextRun();
  else
    GateGenericSource::PrepareNextRun();
}

void GateFastY90Source::GeneratePrimaries(G4Event *event,
                                          double current_simulation_time) {
  if (fInitConfine) {
    fSPS->GetPosDist()->ConfineSourceToVolume(fConfineVolume);
    fInitConfine = false;
  }
  auto position = fSPS->GetPosDist()->VGenerateOne();
  const auto radialDirection = G4RandomDirection();
  auto momentumDirection = radialDirection;
  auto *definition = fParticleDefinition;
  double energy;
  if (fKernel.IsPositron(G4UniformRand())) {
    definition = fPositronDefinition;
    energy = fKernel.SamplePositronEnergy(G4UniformRand()) * CLHEP::MeV;
  } else {
    const auto energyMeV =
        fKernel.SampleBremsstrahlungEnergy(G4UniformRand(), G4UniformRand());
    energy = energyMeV * CLHEP::MeV;
    const auto range =
        fKernel.SampleRange(energyMeV, G4UniformRand(), G4UniformRand());
    position += range * CLHEP::mm * radialDirection;
    const auto angle =
        fKernel.SampleAngle(energyMeV, G4UniformRand(), G4UniformRand());
    const auto azimuth = CLHEP::twopi * G4UniformRand();
    // rotateUz supplies the local spherical basis used by GATE 9 PerturbVector.
    momentumDirection =
        G4ThreeVector(std::sin(angle) * std::cos(azimuth),
                      std::sin(angle) * std::sin(azimuth), std::cos(angle));
    momentumDirection.rotateUz(radialDirection);
  }

  auto *particle = new G4PrimaryParticle(definition);
  particle->SetKineticEnergy(energy);
  particle->SetMomentumDirection(momentumDirection);
  auto *vertex = new G4PrimaryVertex(position, current_simulation_time);
  if (fWeight > 0)
    vertex->SetWeight(
        fWeightSigma < 0 ? fWeight : G4RandGauss::shoot(fWeight, fWeightSigma));
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);
  fRunGeneratedEvents++;
}
