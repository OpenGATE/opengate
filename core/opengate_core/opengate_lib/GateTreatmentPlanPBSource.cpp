#include "GateTreatmentPlanPBSource.h"
#include "G4IonTable.hh"
#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GateHelpersDict.h"
#include "GateHelpersGeometry.h"
#include <G4UnitsTable.hh>

GateTreatmentPlanPBSource::GateTreatmentPlanPBSource() : GateVSource() {
  // fNumberOfGeneratedEvents = 0; // Keeps truck of nb events per RUN
  fParticleDefinition = nullptr;
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

GateTreatmentPlanPBSource::threadLocalTPSource &
GateTreatmentPlanPBSource::GetThreadLocalDataTPSource() {
  return fThreadLocalDataTPSource.Get();
}

void GateTreatmentPlanPBSource::InitializeUserInfo(py::dict &user_info) {
  GateVSource::InitializeUserInfo(user_info);
  auto &ll = GetThreadLocalDataTPSource();
  // Create single particle source only once. Parameters are then updated for
  // the different spots.
  ll.fSPS_PB = new GateSingleParticleSourcePencilBeam(std::string(),
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
  ll.fNbGeneratedSpots.resize(fTotalNumberOfSpots,
                              0); // keep track for debug

  // Init the random fEngine
  InitRandomEngine();
  // assign n_particles to each spot, in case of sorted generation
  if (fSortedSpotGenerationFlag) {
    InitNbPrimariesVec();
  }
}

void GateTreatmentPlanPBSource::InitNbPrimariesVec() {
  auto &ll = GetThreadLocalDataTPSource();
  // Initialize all spots to zero particles
  ll.fNbIonsToGenerate.resize(fTotalNumberOfSpots, 0);
  for (long int i = 0; i < fMaxN; i++) {
    int bin = fTotalNumberOfSpots * fDistriGeneral->fire();
    ++ll.fNbIonsToGenerate[bin];
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
GateTreatmentPlanPBSource::PrepareNextTime(double current_simulation_time,
                                           double NumberOfGeneratedEvents) {

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

  auto &ll = GetThreadLocalDataTPSource();
  // Find next spot to initialize
  FindNextSpot();
  // if we moved to a new spot, we need to update the SPS parameters
  if (ll.fCurrentSpot != ll.fPreviousSpot) {
    ConfigureSingleSpot();
  }

  // Generate vertex
  ll.fSPS_PB->SetParticleTime(current_simulation_time);
  ll.fSPS_PB->GeneratePrimaryVertex(event);

  // weight
  double w = fSpotWeight[ll.fCurrentSpot];
  for (auto i = 0; i < event->GetNumberOfPrimaryVertex(); i++) {
    event->GetPrimaryVertex(i)->SetWeight(w);
  }

  // update number of generated events
  // fNumberOfGeneratedEvents++;
  ll.fNbGeneratedSpots[ll.fCurrentSpot]++;

  if (fSortedSpotGenerationFlag) {
    // we generated an ion from this spot, so we remove it from the vector
    --ll.fNbIonsToGenerate[ll.fCurrentSpot];
  }
  // update previous spot
  ll.fPreviousSpot = ll.fCurrentSpot;
}

void GateTreatmentPlanPBSource::FindNextSpot() {
  auto &ll = GetThreadLocalDataTPSource();
  if (fSortedSpotGenerationFlag) {
    // move to next spot if there are no more particles to generate in the
    // current one
    while ((ll.fCurrentSpot < fTotalNumberOfSpots) &&
           (ll.fNbIonsToGenerate[ll.fCurrentSpot] <= 0)) {
      ll.fCurrentSpot++;
    }

  } else {
    // select random spot according to PDF
    int bin = fTotalNumberOfSpots * fDistriGeneral->fire();
    ll.fCurrentSpot = bin;
  }
}

void GateTreatmentPlanPBSource::ConfigureSingleSpot() {
  auto &ll = GetThreadLocalDataTPSource();
  // Particle definition if ion
  if (ll.fInitGenericIon) {
    auto *ion_table = G4IonTable::GetIonTable();
    auto *ion = ion_table->GetIon(fZ, fA, fE);
    ll.fSPS_PB->SetParticleDefinition(ion);
    ll.fInitGenericIon = false; // only the first time
  }
  // Energy
  double energy = fSpotEnergy[ll.fCurrentSpot];
  double sigmaE = fSigmaEnergy[ll.fCurrentSpot];
  UpdateEnergySPS(energy, sigmaE);

  // rotation and translation
  G4ThreeVector translation = fSpotPosition[ll.fCurrentSpot];
  G4RotationMatrix rotation = fSpotRotation[ll.fCurrentSpot];
  UpdatePositionSPS(translation, rotation);

  // Phase space parameters
  std::vector<double> x_param = fPhSpaceX[ll.fCurrentSpot];
  std::vector<double> y_param = fPhSpaceY[ll.fCurrentSpot];
  ll.fSPS_PB->SetPBSourceParam(x_param, y_param);
}

void GateTreatmentPlanPBSource::UpdatePositionSPS(
    const G4ThreeVector &localTransl, const G4RotationMatrix &localRot) {

  // update local translation and rotation
  auto &ll = GetThreadLocalDataTPSource();
  auto &l = fThreadLocalData.Get();

  l.fGlobalTranslation = localTransl;
  l.fGlobalRotation = localRot; // ConvertToG4RotationMatrix(localRot);

  //   // update global rotation
  //   GateVSource::SetOrientationAccordingToAttachedVolume();

  // No change in the translation rotation if mother is the world
  if (fAttachedToVolumeName == "world") {
    // set it to the vertex
    ll.fSPS_PB->SetSourceRotTransl(l.fGlobalTranslation, l.fGlobalRotation);
    return;
  }

  // compute global translation rotation.
  // l.fGlobalTranslation and l.fGlobalRotation values are updated here.
  ComputeTransformationFromVolumeToWorld(
      fAttachedToVolumeName, l.fGlobalTranslation, l.fGlobalRotation, false);

  // set it to the vertex
  ll.fSPS_PB->SetSourceRotTransl(l.fGlobalTranslation, l.fGlobalRotation);
}

void GateTreatmentPlanPBSource::UpdateEnergySPS(double energy, double sigma) {
  auto &ll = GetThreadLocalDataTPSource();
  auto *ene = ll.fSPS_PB->GetEneDist();
  ene->SetEnergyDisType("Gauss");
  ene->SetMonoEnergy(energy);
  ene->SetBeamSigmaInE(sigma);
}

void GateTreatmentPlanPBSource::InitializeParticle(py::dict &user_info) {
  auto &ll = GetThreadLocalDataTPSource();
  std::string pname = DictGetStr(user_info, "particle");
  // If the particle is an ion (name start with ion)
  if (pname.rfind("ion", 0) == 0) {
    InitializeIon(user_info);
    return;
  }
  // If the particle is not an ion
  // fInitGenericIon = false;
  auto *particle_table = G4ParticleTable::GetParticleTable();
  fParticleDefinition = particle_table->FindParticle(pname);
  if (fParticleDefinition == nullptr) {
    Fatal("Cannot find the particle '" + pname + "'.");
  }
  ll.fSPS_PB->SetParticleDefinition(fParticleDefinition);
}

void GateTreatmentPlanPBSource::InitializeIon(py::dict &user_info) {
  auto &ll = GetThreadLocalDataTPSource();
  auto u = py::dict(user_info["ion"]);
  fA = DictGetInt(u, "A");
  fZ = DictGetInt(u, "Z");
  fE = DictGetDouble(u, "E");
  ll.fInitGenericIon = true;
}

py::list GateTreatmentPlanPBSource::GetGeneratedPrimaries() {
  py::list n_spot_vec;
  //   for (const auto &item : fNbGeneratedSpots) {
  //     n_spot_vec.append(item);
  //   }

  return n_spot_vec;
}
