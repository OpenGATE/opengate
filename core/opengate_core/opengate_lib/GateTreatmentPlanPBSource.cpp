#include "GateTreatmentPlanPBSource.h"
#include "G4IonTable.hh"
#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GateHelpersDict.h"
#include <G4UnitsTable.hh>

GateTreatmentPlanPBSource::GateTreatmentPlanPBSource() : GateVSource() {
  fSPS_PB = nullptr;
  fCurrentSpot = 0;
  fPreviousSpot = -1;
  fNumberOfGeneratedEvents = 0; // Keeps truck of nb events per RUN
  fParticleDefinition = nullptr;
  fInitGenericIon = false;
  fA = 0;
  fZ = 0;
  fE = 0;
  fEngine = nullptr;
  fDistriGeneral = nullptr;
  fSortedSpotGenerationFlag = false;
  fPDF = nullptr;
  fTotalNumberOfSpots = 0;
}

GateTreatmentPlanPBSource::~GateTreatmentPlanPBSource() = default;

void GateTreatmentPlanPBSource::InitializeUserInfo(py::dict &user_info) {
  GateVSource::InitializeUserInfo(user_info);
  // Create single particle source only once. Parameters are then updated for
  // the different spots.
  fSPS_PB = new GateSingleParticleSourcePencilBeam(std::string(),
                                                   fAttachedToVolumeName);

  // common to all spots
  InitializeParticle(user_info);
  std::vector<double> mPDFVector = DictGetVecDouble(user_info, "pdf");
  fPDF = mPDFVector.data(); // returns pointer to first element of the array
  fSortedSpotGenerationFlag = DictGetBool(user_info, "sorted_spot_generation");

  // vectors with info for each spot
  fSpotWeight = DictGetVecDouble(user_info, "weights");
  fSpotEnergy = DictGetVecDouble(user_info, "energies");
  fSigmaEnergy = DictGetVecDouble(user_info, "energy_sigmas");
  fPhSpaceX = DictGetVecofVecDouble(user_info, "partPhSp_xV");
  fPhSpaceY = DictGetVecofVecDouble(user_info, "partPhSp_yV");

  fSpotPosition = DictGetVecG4ThreeVector(user_info, "positions");
  fSpotRotation = DictGetVecG4RotationMatrix(user_info, "rotations");

  fTotalNumberOfSpots = fSpotWeight.size();
  fNbGeneratedSpots.resize(fTotalNumberOfSpots,
                           0); // keep track for debug

  // Init the random fEngine
  InitRandomEngine();
  // assign n_particles to each spot, in case of sorted generation
  if (fSortedSpotGenerationFlag) {
    InitNbPrimariesVec();
  }
}

void GateTreatmentPlanPBSource::InitNbPrimariesVec() {
  // Initialize all spots to zero particles
  fNbIonsToGenerate.resize(fTotalNumberOfSpots, 0);
  for (long int i = 0; i < fMaxN; i++) {
    int bin = fTotalNumberOfSpots * fDistriGeneral->fire();
    ++fNbIonsToGenerate[bin];
  }
}
void GateTreatmentPlanPBSource::InitRandomEngine() {
  fEngine = new CLHEP::HepJamesRandom();
  fDistriGeneral =
      new CLHEP::RandGeneral(fEngine, fPDF, fTotalNumberOfSpots, 0);
}

double GateTreatmentPlanPBSource::CalcNextTime(double current_simulation_time) {
  double fakeActivity = (double)fMaxN * CLHEP::Bq; // 1e-9;
  double timeDelta = (1.0 / fakeActivity);
  double next_time = current_simulation_time + timeDelta;
  return next_time;
}

double
GateTreatmentPlanPBSource::PrepareNextTime(double current_simulation_time) {
  if (current_simulation_time < fStartTime) {
    return fStartTime;
  }
  if (current_simulation_time >= fEndTime) {
    return -1;
  }

  // increment simulation time
  double next_time = CalcNextTime(current_simulation_time);
  if (next_time >= fEndTime) {
    return -1;
  }

  return next_time;
}

void GateTreatmentPlanPBSource::PrepareNextRun() {
  // The following compute the global transformation from
  // the local volume (attached_to) to the world
  GateVSource::PrepareNextRun();
}

void GateTreatmentPlanPBSource::GeneratePrimaries(
    G4Event *event, double current_simulation_time) {

  // Find next spot to initialize
  FindNextSpot();
  // if we moved to a new spot, we need to update the SPS parameters
  if (fCurrentSpot != fPreviousSpot) {
    ConfigureSingleSpot();
  }

  // Generate vertex
  fSPS_PB->SetParticleTime(current_simulation_time);
  fSPS_PB->GeneratePrimaryVertex(event);

  // weight
  double w = fSpotWeight[fCurrentSpot];
  for (auto i = 0; i < event->GetNumberOfPrimaryVertex(); i++) {
    event->GetPrimaryVertex(i)->SetWeight(w);
  }

  // update number of generated events
  fNumberOfGeneratedEvents++;
  fNbGeneratedSpots[fCurrentSpot]++;

  if (fSortedSpotGenerationFlag) {
    // we generated an ion from this spot, so we remove it from the vector
    --fNbIonsToGenerate[fCurrentSpot];
  }
  // update previous spot
  fPreviousSpot = fCurrentSpot;
}

void GateTreatmentPlanPBSource::FindNextSpot() {
  if (fSortedSpotGenerationFlag) {
    // move to next spot if there are no more particles to generate in the
    // current one
    while ((fCurrentSpot < fTotalNumberOfSpots) &&
           (fNbIonsToGenerate[fCurrentSpot] <= 0)) {
      fCurrentSpot++;
    }

  } else {
    // select random spot according to PDF
    int bin = fTotalNumberOfSpots * fDistriGeneral->fire();
    fCurrentSpot = bin;
  }
}

void GateTreatmentPlanPBSource::ConfigureSingleSpot() {
  // Particle definition if ion
  if (fInitGenericIon) {
    auto *ion_table = G4IonTable::GetIonTable();
    auto *ion = ion_table->GetIon(fZ, fA, fE);
    fSPS_PB->SetParticleDefinition(ion);
    fInitGenericIon = false; // only the first time
  }
  // Energy
  double energy = fSpotEnergy[fCurrentSpot];
  double sigmaE = fSigmaEnergy[fCurrentSpot];
  UpdateEnergySPS(energy, sigmaE);

  // rotation and translation
  G4ThreeVector translation = fSpotPosition[fCurrentSpot];
  G4RotationMatrix rotation = fSpotRotation[fCurrentSpot];
  UpdatePositionSPS(translation, rotation);

  // Phase space parameters
  std::vector<double> x_param = fPhSpaceX[fCurrentSpot];
  std::vector<double> y_param = fPhSpaceY[fCurrentSpot];
  fSPS_PB->SetPBSourceParam(x_param, y_param);
}

void GateTreatmentPlanPBSource::UpdatePositionSPS(
    const G4ThreeVector &localTransl, const G4RotationMatrix &localRot) {

  // update local translation and rotation
  auto &l = fThreadLocalData.Get();
  fLocalTranslation = localTransl;
  fLocalRotation = localRot; // ConvertToG4RotationMatrix(localRot);

  // update global rotation
  GateVSource::SetOrientationAccordingToAttachedVolume();

  // set it to the vertex
  fSPS_PB->SetSourceRotTransl(l.fGlobalTranslation, l.fGlobalRotation);
}

void GateTreatmentPlanPBSource::UpdateEnergySPS(double energy, double sigma) {
  auto *ene = fSPS_PB->GetEneDist();
  ene->SetEnergyDisType("Gauss");
  ene->SetMonoEnergy(energy);
  ene->SetBeamSigmaInE(sigma);
}

void GateTreatmentPlanPBSource::InitializeParticle(py::dict &user_info) {
  std::string pname = DictGetStr(user_info, "particle");
  // If the particle is an ion (name start with ion)
  if (pname.rfind("ion", 0) == 0) {
    InitializeIon(user_info);
    return;
  }
  // If the particle is not an ion
  fInitGenericIon = false;
  auto *particle_table = G4ParticleTable::GetParticleTable();
  fParticleDefinition = particle_table->FindParticle(pname);
  if (fParticleDefinition == nullptr) {
    Fatal("Cannot find the particle '" + pname + "'.");
  }
  fSPS_PB->SetParticleDefinition(fParticleDefinition);
}

void GateTreatmentPlanPBSource::InitializeIon(py::dict &user_info) {
  auto u = py::dict(user_info["ion"]);
  fA = DictGetInt(u, "A");
  fZ = DictGetInt(u, "Z");
  fE = DictGetDouble(u, "E");
  fInitGenericIon = true;
}

py::list GateTreatmentPlanPBSource::GetGeneratedPrimaries() {
  py::list n_spot_vec;
  for (const auto &item : fNbGeneratedSpots) {
    n_spot_vec.append(item);
  }

  return n_spot_vec;
}
