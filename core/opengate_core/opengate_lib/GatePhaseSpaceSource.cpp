/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePhaseSpaceSource.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersPyBind.h"
#include <G4IonTable.hh>
#include <G4ParticleTable.hh>
#include <Randomize.hh>

GatePhaseSpaceSource::GatePhaseSpaceSource() : GateVSource() {
  fCharge = 0;
  fMass = 0;
  fGlobalFag = false;
  fVerbose = false;
  fParticleTable = nullptr;
  fUseParticleTypeFromFile = false;
  fParticleDefinition = nullptr;
}

GatePhaseSpaceSource::~GatePhaseSpaceSource() = default;

void GatePhaseSpaceSource::InitializeUserInfo(py::dict &user_info) {
  GateVSource::InitializeUserInfo(user_info);

  // global (world) or local (mother volume) coordinate system
  fGlobalFag = DictGetBool(user_info, "global_flag");

  fVerbose = DictGetInt(user_info, "verbose");
  fIsotropicMomentum = DictGetBool(user_info, "isotropic_direction");

  // This is done in GateSingleParticleSource, but we need charge/mass later
  auto pname = DictGetStr(user_info, "particle");
  fParticleTable = G4ParticleTable::GetParticleTable();
  // if particle left empty, the particle type will be read from the phsp file
  // check length of particle name
  if (pname.length() == 0 || pname == "None")
    fUseParticleTypeFromFile = true;
  else {
    fUseParticleTypeFromFile = false;
    fParticleDefinition = fParticleTable->FindParticle(pname);
    if (fParticleDefinition == nullptr) {
      Fatal("GatePhaseSpaceSource: PDGCode not found. Aborting.");
    }
    fCharge = static_cast<std::float_t>(fParticleDefinition->GetPDGCharge());
    fMass = static_cast<std::float_t>(fParticleDefinition->GetPDGMass());
  }

  // Init
  fRunGeneratedEvents = 0;
  fCurrentIndex = 0;
  fCurrentBatchSize = 0;

  fGenerateUntilNextPrimary =
      DictGetBool(user_info, "generate_until_next_primary");
  fPrimaryLowerEnergyThreshold =
      DictGetDouble(user_info, "primary_lower_energy_threshold");
  fPrimaryPDGCode = DictGetInt(user_info, "primary_PDGCode");
}

void GatePhaseSpaceSource::PrepareNextRun() {
  // needed to update orientation wrt mother volume
  GateVSource::PrepareNextRun();
}

void GatePhaseSpaceSource::SetGeneratorFunction(ParticleGeneratorType &f) {
  fGenerator = f;
}

void GatePhaseSpaceSource::GenerateBatchOfParticles() {
  // I don't know if we should acquire the GIL or not
  // (does not seem needed)
  // py::gil_scoped_acquire acquire;

  // This function (fGenerator) is defined on Python side
  // It fills all values needed for the particles (position, dir, energy, etc)
  // Alternative: build vector of G4ThreeVector in GenerateBatchOfParticles ?
  // (unsure if it is faster)
  fCurrentBatchSize = fGenerator(this, G4Threading::G4GetThreadId());
  fCurrentIndex = 0;
}

void GatePhaseSpaceSource::GeneratePrimaries(G4Event *event,
                                             double current_simulation_time) {
  // check if we should simulate until next primary
  // in this case, generate until a second primary is in the list, excluding the
  // second primary

  // If batch is empty, we generate some particles, could happen at the first
  // execution
  if (fCurrentBatchSize == 0) {
    GenerateBatchOfParticles();
  }

  if (fGenerateUntilNextPrimary) {
    int num_primaries = 0;
    while (num_primaries <= 2) {
      // If batch is empty, we generate some particles
      if (fCurrentIndex >= fCurrentBatchSize)
        GenerateBatchOfParticles();

      // check if next particle is primary
      if (ParticleIsPrimary())
        num_primaries++;

      // don't generate the second primary
      if (num_primaries < 2) {
        // Create vertex and particle, if called more than once
        // multiple vertices and particles exist in the event
        // Geant4 will only print the first one, but generate all of them
        GenerateOnePrimary(event, current_simulation_time);

        // update the root file index;
        fCurrentIndex++;
      } else
        break;
    }
    // update the number of generated event
    fRunGeneratedEvents++;
  }

  else {
    // If batch is empty, we generate some particles
    if (fCurrentIndex >= fCurrentBatchSize)
      GenerateBatchOfParticles();
    // Go
    GenerateOnePrimary(event, current_simulation_time);

    // update the root file index;
    fCurrentIndex++;

    // update the number of generated event
    fRunGeneratedEvents++;
  }
}

G4ParticleMomentum GatePhaseSpaceSource::GenerateRandomDirection() {
  G4double cosTheta = 2.0 * G4UniformRand() - 1.0;
  G4double sinTheta = std::sqrt(1.0 - cosTheta * cosTheta);
  G4double phi = 2.0 * CLHEP::pi * G4UniformRand();
  G4double x = sinTheta * std::cos(phi);
  G4double y = sinTheta * std::sin(phi);
  G4double z = cosTheta;

  return G4ParticleMomentum(x, y, z);
}

void GatePhaseSpaceSource::GenerateOnePrimary(G4Event *event,
                                              double current_simulation_time) {
  G4ThreeVector position(fPositionX[fCurrentIndex], fPositionY[fCurrentIndex],
                         fPositionZ[fCurrentIndex]);

  G4ParticleMomentum direction;
  if (fIsotropicMomentum == false) {
    direction = G4ParticleMomentum(fDirectionX[fCurrentIndex],
                                   fDirectionY[fCurrentIndex],
                                   fDirectionZ[fCurrentIndex]);
  }

  else {
    direction = GenerateRandomDirection();
  }
  auto energy = fEnergy[fCurrentIndex];
  auto weight = fWeight[fCurrentIndex];

  // FIXME auto time = fTime[fCurrentIndex];

  // transform according to mother
  if (!fGlobalFag) {
    position = fGlobalRotation * position + fGlobalTranslation;
    direction = direction / direction.mag();
    direction = fGlobalRotation * direction;
  }
  // Create the final vertex
  AddOnePrimaryVertex(event, position, direction, energy,
                      current_simulation_time, weight);
}

void GatePhaseSpaceSource::AddOnePrimaryVertex(G4Event *event,
                                               const G4ThreeVector &position,
                                               const G4ThreeVector &direction,
                                               double energy, double time,
                                               double w) {
  auto *particle = new G4PrimaryParticle();
  if (fUseParticleTypeFromFile) {
    auto pdg = fPDGCode[fCurrentIndex];
    if (fPDGCode[fCurrentIndex] != 0) {
      // find if particle exists
      fParticleDefinition = fParticleTable->FindParticle(pdg);
      // if not, find if it is an ion
      if (fParticleDefinition == nullptr) {
        G4IonTable *ionTable = fParticleTable->GetIonTable();
        fParticleDefinition = ionTable->GetIon(pdg);
      }
      if (fParticleDefinition == nullptr) {
        Fatal("GatePhaseSpaceSource: PDGCode not found. Aborting.");
      }
      particle->SetParticleDefinition(fParticleDefinition);
    } else {
      Fatal("GatePhaseSpaceSource: PDGCode not available. Aborting.");
    }
  } else {
    particle->SetParticleDefinition(fParticleDefinition);
    particle->SetMass(fMass);
    particle->SetCharge(fCharge);
  }
  particle->SetKineticEnergy(energy);
  particle->SetMomentumDirection(direction);

  // set vertex
  auto *vertex = new G4PrimaryVertex(position, time);
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);
  // weights
  event->GetPrimaryVertex(0)->SetWeight(w);
  if (fVerbose) {
    std::cout << "Particle PDGCode: " << fParticleDefinition->GetPDGEncoding()
              << " Energy: " << energy << " Weight: " << w
              << " Position: " << position << " Direction: " << direction
              << " Time: " << time << " EventID: " << event->GetEventID()
              << std::endl;
  }
}

void GatePhaseSpaceSource::SetPDGCodeBatch(
    const py::array_t<std::int32_t> &fPDGCode) {
  this->fPDGCode = PyBindGetVector<std::int32_t>(fPDGCode);
}

void GatePhaseSpaceSource::SetEnergyBatch(
    const py::array_t<std::float_t> &fEnergy) {
  this->fEnergy = PyBindGetVector(fEnergy);
}

void GatePhaseSpaceSource::SetWeightBatch(
    const py::array_t<std::float_t> &fWeight) {
  this->fWeight = PyBindGetVector(fWeight);
}

void GatePhaseSpaceSource::SetPositionXBatch(
    const py::array_t<std::float_t> &fPositionX) {
  this->fPositionX = PyBindGetVector(fPositionX);
}

void GatePhaseSpaceSource::SetPositionYBatch(
    const py::array_t<std::float_t> &fPositionY) {
  this->fPositionY = PyBindGetVector(fPositionY);
}

void GatePhaseSpaceSource::SetPositionZBatch(
    const py::array_t<std::float_t> &fPositionZ) {
  this->fPositionZ = PyBindGetVector(fPositionZ);
}

void GatePhaseSpaceSource::SetDirectionXBatch(
    const py::array_t<std::float_t> &fDirectionX) {
  this->fDirectionX = PyBindGetVector(fDirectionX);
}

void GatePhaseSpaceSource::SetDirectionYBatch(
    const py::array_t<std::float_t> &fDirectionY) {
  this->fDirectionY = PyBindGetVector(fDirectionY);
}

void GatePhaseSpaceSource::SetDirectionZBatch(
    const py::array_t<std::float_t> &fDirectionZ) {
  this->fDirectionZ = PyBindGetVector(fDirectionZ);
}

bool GatePhaseSpaceSource::ParticleIsPrimary() const {
  // check if particle is primary
  bool is_primary = false;

  // if PDGCode exists in file
  if ((fPDGCode[fCurrentIndex] != 0) && (fPrimaryPDGCode != 0)) {
    if ((fPrimaryPDGCode == fPDGCode[fCurrentIndex]) &&
        (fPrimaryLowerEnergyThreshold <= fEnergy[fCurrentIndex])) {
      is_primary = true;
    }
  } else {
    G4Exception("GatePhaseSpaceSource::ParticleIsPrimary", "Error",
                FatalException, "Particle type not defined in file");
    std::cout << "ERROR: PDGCode not defined in file. Aborting." << std::endl;
    exit(1);
  }

  return is_primary;
}
