/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePhaseSpaceSource.h"
#include "G4ParticleTable.hh"
#include "G4UnitsTable.hh"
#include "GateHelpersDict.h"

GatePhaseSpaceSource::GatePhaseSpaceSource() : GateVSource() {
  fCurrentIndex = INT_MAX;
  fCharge = 0;
  fMass = 0;
  fCurrentBatchSize = 0;
  fMaxN = 0;
  fGlobalFag = false;
}

GatePhaseSpaceSource::~GatePhaseSpaceSource() = default;

void GatePhaseSpaceSource::InitializeUserInfo(py::dict &user_info) {
  // the following initialize all GenericSource options
  // and the SPS GateSingleParticleSource
  GateVSource::InitializeUserInfo(user_info);

  // Number of events to generate
  fMaxN = DictGetInt(user_info, "n");

  // Batch size
  fCurrentBatchSize = DictGetInt(user_info, "batch_size");

  // global (world) or local (mother volume) coordinate system
  fGlobalFag = DictGetBool(user_info, "global_flag");

  // This is done in GateSingleParticleSource, but we need charge/mass later
  auto pname = DictGetStr(user_info, "particle");
  fParticleTable = G4ParticleTable::GetParticleTable();
  // if particle left empty, the particle type will be read from the phsp file
  // check length of particle name
  if (pname.length() == 0)
    fUseParticleTypeFromFile = true;
  else {
    fUseParticleTypeFromFile = false;
    fParticleDefinition = fParticleTable->FindParticle(pname);
    fCharge = fParticleDefinition->GetPDGCharge();
    fMass = fParticleDefinition->GetPDGMass();
  }

  fgenerate_until_next_primary =
      DictGetBool(user_info, "generate_until_next_primary");
  fprimary_lower_energy_threshold =
      DictGetDouble(user_info, "primary_lower_energy_threshold");
  fprimary_PDGCode = DictGetInt(user_info, "primary_PDGCode");
  fprimary_pname = DictGetStr(user_info, "primary_particle_name");

  // Init
  fNumberOfGeneratedEvents = 0;
  fCurrentIndex = -1;
}

void GatePhaseSpaceSource::PrepareNextRun() {
  // needed to update orientation wrt mother volume
  // (no need to update th fSPS pos in GateGenericSource)
  // GateVSource::PrepareNextRun();
  // FIXME remove this function ?
  GateVSource::PrepareNextRun();
}

double GatePhaseSpaceSource::PrepareNextTime(double current_simulation_time) {
  // check according to t MaxN
  if (fNumberOfGeneratedEvents >= fMaxN) {
    return -1;
  }
  return fStartTime; // FIXME timing ?
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
  fGenerator(this);
  fCurrentIndex = 0;
  fCurrentBatchSize = fPositionX.size();
}

void GatePhaseSpaceSource::GeneratePrimaries(G4Event *event,
                                             double current_simulation_time) {
  // check if we should simulate until next primary
  // in this case, generate until a second primary is in the list, excluding the
  // second primary
  if (fgenerate_until_next_primary) {
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
        // Go
        GenerateOnePrimary(event, current_simulation_time);

        // update the index;
        fCurrentIndex++;

        // // update the number of generated event
        // fNumberOfGeneratedEvents++;
      } else
        break;
    }
    // update the number of generated event
    fNumberOfGeneratedEvents++;
  }

  else {
    // If batch is empty, we generate some particles
    if (fCurrentIndex >= fCurrentBatchSize)
      GenerateBatchOfParticles();

    // Go
    GenerateOnePrimary(event, current_simulation_time);

    // update the index;
    fCurrentIndex++;

    // update the number of generated event
    fNumberOfGeneratedEvents++;
  }
}

void GatePhaseSpaceSource::GenerateOnePrimary(G4Event *event,
                                              double current_simulation_time) {
  auto position =
      G4ThreeVector(fPositionX[fCurrentIndex], fPositionY[fCurrentIndex],
                    fPositionZ[fCurrentIndex]);
  auto direction =
      G4ParticleMomentum(fDirectionX[fCurrentIndex], fDirectionY[fCurrentIndex],
                         fDirectionZ[fCurrentIndex]);
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

// void GatePhaseSpaceSource::AddOnePrimaryVertex(G4Event *event,
//                                                const G4ThreeVector &position,
//                                                const G4ThreeVector
//                                                &direction, double energy,
//                                                double time, double w) const
void GatePhaseSpaceSource::AddOnePrimaryVertex(G4Event *event,
                                               const G4ThreeVector &position,
                                               const G4ThreeVector &direction,
                                               double energy, double time,
                                               double w) {

  auto *particle = new G4PrimaryParticle();
  // if we use the particle type from the file, there are two options
  // 1) the PDGCodee is not defined in the file
  // 2) the particle name is not defined in the file
  if (fUseParticleTypeFromFile == true) {
    // if PDGCode exists in file
    if (fPDGCode[fCurrentIndex] != 0) {
      // auto *particle_table = G4ParticleTable::GetParticleTable();
      fParticleDefinition =
          fParticleTable->FindParticle(fPDGCode[fCurrentIndex]);
      particle->SetParticleDefinition(fParticleDefinition);
    }
    // if PDGCode does not exist in file, but particle name does and is not
    // empty
    else if (fParticleName[fCurrentIndex].length() != 0) {
      // auto *particle_table = G4ParticleTable::GetParticleTable();
      fParticleDefinition =
          fParticleTable->FindParticle(fParticleName[fCurrentIndex]);
      fCharge = fParticleDefinition->GetPDGCharge();
      fMass = fParticleDefinition->GetPDGMass();
      particle->SetParticleDefinition(fParticleDefinition);
    } else {
      G4Exception("GatePhaseSpaceSource::AddOnePrimaryVertex", "Error",
                  FatalException, "Particle type not defined in file");
      std::cout << "ERROR: Particle name nor PDGCode defined in file. Aborting."
                << std::endl;
      exit(1);
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
}

bool GatePhaseSpaceSource::ParticleIsPrimary() {
  // check if particle is primary
  bool is_primary = false;

  // if PDGCode exists in file
  if ((fPDGCode[fCurrentIndex] != 0) && (fprimary_PDGCode != 0)) {
    if ((fprimary_PDGCode == fPDGCode[fCurrentIndex]) &&
        (fprimary_lower_energy_threshold <= fEnergy[fCurrentIndex])) {
      is_primary = true;
    }
  }
  // if PDGCode does not exist in file, but particle name does and is not
  // empty
  else if ((fParticleName[fCurrentIndex].length() != 0) &&
           (fprimary_pname.length() != 0)) {
    if ((fprimary_pname == fParticleName[fCurrentIndex]) &&
        (fprimary_lower_energy_threshold <= fEnergy[fCurrentIndex])) {
      is_primary = true;
    }
  } else {
    G4Exception("GatePhaseSpaceSource::ParticleIsPrimary", "Error",
                FatalException, "Particle type not defined in file");
    std::cout << "ERROR: Particle name nor PDGCode defined in file. Aborting."
              << std::endl;
    exit(1);
  }

  return is_primary;
}
