/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePBSource.h"
#include "G4IonTable.hh"
#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GateHelpersDict.h"
#include <G4UnitsTable.hh>

GatePBSource::GatePBSource() : GateGenericSource() {}

GatePBSource::~GatePBSource() {}

void GatePBSource::InitializeUserInfo(py::dict &user_info) {

  GateVSource::InitializeUserInfo(user_info);
  fSPS = new GateSingleParticleSource(fMother);

  // get user info about activity or nb of events
  fMaxN = DictGetInt(user_info, "n");
  fActivity = DictGetDouble(user_info, "activity");
  fInitialActivity = fActivity;

  // half life ?
  fHalfLife = DictGetDouble(user_info, "half_life");
  fLambda = log(2) / fHalfLife;

  // weight
  fWeight = DictGetDouble(user_info, "weight");
  fWeightSigma = DictGetDouble(user_info, "weight_sigma");

  // get the user info for the particle
  GateGenericSource::InitializeParticle(user_info);

  // position, direction, energy
  InitializePosition(user_info);
  GateGenericSource::InitializeDirection(user_info);
  GateGenericSource::InitializeEnergy(user_info);

  // FIXME todo polarization

  // init number of events
  fNumberOfGeneratedEvents = 0;
  // FIXME fNotAcceptedEvents = 0;
}

void GatePBSource::PrepareNextRun() {
  // The following compute the global transformation from
  // the local volume (mother) to the world
  GateVSource::PrepareNextRun();
  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
  // translation
  fSPS->SetSourceRotTransl(fGlobalTranslation, fGlobalRotation);
}

void GatePBSource::InitializePosition(py::dict puser_info) {

  auto user_info = py::dict(puser_info["position"]);
  auto *pos = fSPS->GetPosDist();
  auto pos_type = DictGetStr(user_info, "type");
  std::vector<std::string> l = {"sphere", "point", "box", "disc", "cylinder"};
  CheckIsIn(pos_type, l);
  auto translation = DictGetG4ThreeVector(user_info, "translation");
  if (pos_type == "point") {
    pos->SetPosDisType("Point");
  }
  if (pos_type == "box") {
    pos->SetPosDisType("Volume");
    pos->SetPosDisShape("Para");
    auto size = DictGetG4ThreeVector(user_info, "size") / 2.0;
    pos->SetHalfX(size[0]);
    pos->SetHalfY(size[1]);
    pos->SetHalfZ(size[2]);
  }
  if (pos_type == "sphere") {
    pos->SetPosDisType("Volume");
    pos->SetPosDisShape("Sphere");
  }
  if (pos_type == "disc") {
    pos->SetPosDisType("Beam"); // FIXME ?  Cannot be plane
    pos->SetPosDisShape("Circle");
  }
  if (pos_type == "cylinder") {
    pos->SetPosDisType("Volume");
    pos->SetPosDisShape("Cylinder");
    auto dz = DictGetDouble(user_info, "dz");
    pos->SetHalfZ(dz / 2.0);
  }

  // rotation
  auto rotation = DictGetMatrix(user_info, "rotation");

  // save local translation and rotation (will be used in
  // SetOrientationAccordingToMotherVolume)
  fLocalTranslation = translation;
  fLocalRotation = ConvertToG4RotationMatrix(
      rotation); // G4RotationMatrix(colX, colY, colZ);

  // confine to a volume ?
  if (user_info.contains("confine")) {
    auto v = DictGetStr(user_info, "confine");
    if (v != "None") {
      fConfineVolume = v;
      fInitConfine = true;
    }
  }

  // PBS parameters
  auto dir_info = py::dict(puser_info["direction"]);
  fSPS->SetPBSourceParam(dir_info);
}

void GatePBSource::GeneratePrimaries(G4Event *event,
                                     double current_simulation_time) {
  // Generic ion cannot be created at initialization.
  // It must be created here, the first time we get there
  if (fInitGenericIon) {
    auto *ion_table = G4IonTable::GetIonTable();
    auto *ion = ion_table->GetIon(fZ, fA, fE);
    fSPS->SetParticleDefinition(ion);
    InitializeHalfTime(ion);
    fInitGenericIon = false; // only the first time
  }

  // Confine cannot be initialized at initialization (because need all volumes
  // to be created) It must be set here, the first time we get there
  if (fInitConfine) {
    auto *pos = fSPS->GetPosDist();
    pos->ConfineSourceToVolume(fConfineVolume);
    fInitConfine = false;
  }

  // sample the particle properties with SingleParticleSource
  fSPS->SetParticleTime(current_simulation_time);
  fSPS->GeneratePrimaryVertexPB(event);
  // fSPS->GeneratePrimaryVertex(event);

  // weight ?
  if (fWeight > 0) {
    if (fWeightSigma < 0) {
      for (auto i = 0; i < event->GetNumberOfPrimaryVertex(); i++) {
        event->GetPrimaryVertex(i)->SetWeight(fWeight);
      }
    } else { // weight is Gaussian
      for (auto i = 0; i < event->GetNumberOfPrimaryVertex(); i++) {
        double w = G4RandGauss::shoot(fWeight, fWeightSigma);
        event->GetPrimaryVertex(i)->SetWeight(w);
      }
    }
  }

  fNumberOfGeneratedEvents++;
}
