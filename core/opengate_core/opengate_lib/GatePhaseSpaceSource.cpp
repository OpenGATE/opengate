/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePhaseSpaceSource.h"
#include "G4IonTable.hh"
#include "G4ParticleTable.hh"
#include "G4UnitsTable.hh"
#include "GateHelpersDict.h"
#include "GateHelpersPyBind.h"
#include "Randomize.hh"

GatePhaseSpaceSource::GatePhaseSpaceSource() : GateVSource() {
  fCharge = 0;
  fMass = 0;
  fGlobalFag = false;
  fVerbose = false;
  fParticleTable = nullptr;
  fUseParticleTypeFromFile = false;
  auto &l = fThreadLocalDataPhsp.Get();
  l.fParticleDefinition = nullptr;
}

GatePhaseSpaceSource::~GatePhaseSpaceSource() {
  // It seems that this is required to prevent seg fault at the end
  // I don't understand why
  auto &l = fThreadLocalDataPhsp.Get();
}

void GatePhaseSpaceSource::InitializeUserInfo(py::dict &user_info) {
  auto &l = fThreadLocalDataPhsp.Get();
  // the following initialize all GenericSource options
  // and the SPS GateSingleParticleSource
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
    l.fParticleDefinition = fParticleTable->FindParticle(pname);
    if (l.fParticleDefinition == nullptr) {
      Fatal("GatePhaseSpaceSource: PDGCode not found. Aborting.");
    }
    fCharge = l.fParticleDefinition->GetPDGCharge();
    fMass = l.fParticleDefinition->GetPDGMass();
  }

  // Init
  l.fNumberOfGeneratedEvents = 0;
  l.fCurrentIndex = 0;
  l.fCurrentBatchSize = 0;

  l.fGenerateUntilNextPrimary =
      DictGetBool(user_info, "generate_until_next_primary");
  l.fPrimaryLowerEnergyThreshold =
      DictGetDouble(user_info, "primary_lower_energy_threshold");
  l.fPrimaryPDGCode = DictGetInt(user_info, "primary_PDGCode");
}

void GatePhaseSpaceSource::PrepareNextRun() {
  // needed to update orientation wrt mother volume
  GateVSource::PrepareNextRun();
}

double GatePhaseSpaceSource::PrepareNextTime(double current_simulation_time) {
  // check according to t MaxN

  UpdateActivity(current_simulation_time);
  if (fMaxN <= 0) {
    if (current_simulation_time < fStartTime)
      return fStartTime;
    if (current_simulation_time >= fEndTime)
      return -1;

    double next_time = CalcNextTime(current_simulation_time);
    if (next_time >= fEndTime)
      return -1;
    return next_time;
  }
  auto &l = fThreadLocalDataPhsp.Get();
  if (l.fNumberOfGeneratedEvents >= fMaxN) {
    return -1;
  }
  return fStartTime; // FIXME timing ?
}

void GatePhaseSpaceSource::SetGeneratorFunction(
    ParticleGeneratorType &f) const {
  auto &l = fThreadLocalDataPhsp.Get();
  l.fGenerator = f;
}

void GatePhaseSpaceSource::GenerateBatchOfParticles() {
  // I don't know if we should acquire the GIL or not
  // (does not seem needed)
  // py::gil_scoped_acquire acquire;

  // This function (l.fGenerator) is defined on Python side
  // It fills all values needed for the particles (position, dir, energy, etc)
  // Alternative: build vector of G4ThreeVector in GenerateBatchOfParticles ?
  // (unsure if it is faster)
  auto &l = fThreadLocalDataPhsp.Get();
  l.fCurrentBatchSize = l.fGenerator(this, G4Threading::G4GetThreadId());
  l.fCurrentIndex = 0;
}

void GatePhaseSpaceSource::GeneratePrimaries(G4Event *event,
                                             double current_simulation_time) {
  auto &l = fThreadLocalDataPhsp.Get();
  // check if we should simulate until next primary
  // in this case, generate until a second primary is in the list, excluding the
  // second primary

  // If batch is empty, we generate some particles, could happen at the first
  // execution
  if (l.fCurrentBatchSize == 0) {
    GenerateBatchOfParticles();
  }

  if (l.fGenerateUntilNextPrimary) {
    int num_primaries = 0;
    while (num_primaries <= 2) {
      // If batch is empty, we generate some particles
      if (l.fCurrentIndex >= l.fCurrentBatchSize)
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
        l.fCurrentIndex++;
      } else
        break;
    }
    // update the number of generated event
    l.fNumberOfGeneratedEvents++;
  }

  else {
    // If batch is empty, we generate some particles
    if (l.fCurrentIndex >= l.fCurrentBatchSize)
      GenerateBatchOfParticles();
    // Go
    GenerateOnePrimary(event, current_simulation_time);

    // update the root file index;
    l.fCurrentIndex++;

    // update the number of generated event
    l.fNumberOfGeneratedEvents++;
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
  auto &l = fThreadLocalDataPhsp.Get();

  auto position = G4ThreeVector(l.fPositionX[l.fCurrentIndex],
                                l.fPositionY[l.fCurrentIndex],
                                l.fPositionZ[l.fCurrentIndex]);

  G4ParticleMomentum direction;
  if (fIsotropicMomentum == false) {
    direction = G4ParticleMomentum(l.fDirectionX[l.fCurrentIndex],
                                   l.fDirectionY[l.fCurrentIndex],
                                   l.fDirectionZ[l.fCurrentIndex]);
  }

  else {
    direction = GenerateRandomDirection();
  }
  auto energy = l.fEnergy[l.fCurrentIndex];
  auto weight = l.fWeight[l.fCurrentIndex];

  // FIXME auto time = fTime[l.fCurrentIndex];

  // transform according to mother
  if (!fGlobalFag) {
    auto &ls = fThreadLocalData.Get();
    position = ls.fGlobalRotation * position + ls.fGlobalTranslation;
    direction = direction / direction.mag();
    direction = ls.fGlobalRotation * direction;
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
  auto &l = fThreadLocalDataPhsp.Get();
  if (fUseParticleTypeFromFile) {
    auto pdg = l.fPDGCode[l.fCurrentIndex];
    if (l.fPDGCode[l.fCurrentIndex] != 0) {
      // find if particle exists
      l.fParticleDefinition = fParticleTable->FindParticle(pdg);
      // if not, find if it is an ion
      if (l.fParticleDefinition == nullptr) {
        G4IonTable *ionTable = fParticleTable->GetIonTable();
        l.fParticleDefinition = ionTable->GetIon(pdg);
      }
      if (l.fParticleDefinition == nullptr) {
        Fatal("GatePhaseSpaceSource: PDGCode not found. Aborting.");
      }
      particle->SetParticleDefinition(l.fParticleDefinition);
    } else {
      Fatal("GatePhaseSpaceSource: PDGCode not available. Aborting.");
    }
  } else {
    particle->SetParticleDefinition(l.fParticleDefinition);
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
    std::cout << "Particle PDGCode: " << l.fParticleDefinition->GetPDGEncoding()
              << " Energy: " << energy << " Weight: " << w
              << " Position: " << position << " Direction: " << direction
              << " Time: " << time << " EventID: " << event->GetEventID()
              << std::endl;
  }
}

void GatePhaseSpaceSource::SetPDGCodeBatch(
    const py::array_t<std::int32_t> &fPDGCode) const {
  auto &l = fThreadLocalDataPhsp.Get();
  l.fPDGCode = PyBindGetVector<std::int32_t>(fPDGCode);
}

void GatePhaseSpaceSource::SetEnergyBatch(
    const py::array_t<std::float_t> &fEnergy) const {
  auto &l = fThreadLocalDataPhsp.Get();
  l.fEnergy = PyBindGetVector(fEnergy);
}

void GatePhaseSpaceSource::SetWeightBatch(
    const py::array_t<std::float_t> &fWeight) const {
  auto &l = fThreadLocalDataPhsp.Get();
  l.fWeight = PyBindGetVector(fWeight);
}

void GatePhaseSpaceSource::SetPositionXBatch(
    const py::array_t<std::float_t> &fPositionX) const {
  auto &l = fThreadLocalDataPhsp.Get();
  l.fPositionX = PyBindGetVector(fPositionX);
}

void GatePhaseSpaceSource::SetPositionYBatch(
    const py::array_t<std::float_t> &fPositionY) const {
  auto &l = fThreadLocalDataPhsp.Get();
  l.fPositionY = PyBindGetVector(fPositionY);
}

void GatePhaseSpaceSource::SetPositionZBatch(
    const py::array_t<std::float_t> &fPositionZ) const {
  auto &l = fThreadLocalDataPhsp.Get();
  l.fPositionZ = PyBindGetVector(fPositionZ);
}

void GatePhaseSpaceSource::SetDirectionXBatch(
    const py::array_t<std::float_t> &fDirectionX) const {
  auto &l = fThreadLocalDataPhsp.Get();
  l.fDirectionX = PyBindGetVector(fDirectionX);
}

void GatePhaseSpaceSource::SetDirectionYBatch(
    const py::array_t<std::float_t> &fDirectionY) const {
  auto &l = fThreadLocalDataPhsp.Get();
  l.fDirectionY = PyBindGetVector(fDirectionY);
}

void GatePhaseSpaceSource::SetDirectionZBatch(
    const py::array_t<std::float_t> &fDirectionZ) const {
  auto &l = fThreadLocalDataPhsp.Get();
  l.fDirectionZ = PyBindGetVector(fDirectionZ);
}

bool GatePhaseSpaceSource::ParticleIsPrimary() const {
  auto &l = fThreadLocalDataPhsp.Get();
  // check if particle is primary
  bool is_primary = false;

  // if PDGCode exists in file
  if ((l.fPDGCode[l.fCurrentIndex] != 0) && (l.fPrimaryPDGCode != 0)) {
    if ((l.fPrimaryPDGCode == l.fPDGCode[l.fCurrentIndex]) &&
        (l.fPrimaryLowerEnergyThreshold <= l.fEnergy[l.fCurrentIndex])) {
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
