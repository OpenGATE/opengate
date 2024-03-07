#include "GateTreatmentPlanPBSource.h"
#include "G4IonTable.hh"
#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GateHelpersDict.h"
#include <G4UnitsTable.hh>

GateTreatmentPlanPBSource::GateTreatmentPlanPBSource() : GateVSource() {
  fSPS_PB = nullptr;
  mCurrentSpot = 0;
  mPreviousSpot = -1;
  fNumberOfGeneratedEvents = 0;
  fParticleDefinition = nullptr;
  fInitGenericIon = false;
  fA = 0;
  fZ = 0;
  fE = 0;
}

GateTreatmentPlanPBSource::~GateTreatmentPlanPBSource() {}

void GateTreatmentPlanPBSource::InitializeUserInfo(py::dict &user_info) {
  GateVSource::InitializeUserInfo(user_info);
  // Create single particle source only once. Parameters are then updated for
  // the different spots.
  fSPS_PB = new GateSingleParticleSourcePencilBeam(std::string(), fMother);

  // common to all spots
  InitializeParticle(user_info);

  mNbIonsToGenerate = DictGetVecInt(user_info, "n_particles");
  mSortedSpotGenerationFlag = DictGetBool(user_info, "sorted_spot_generation");
  // vectors with info for each spot
  mSpotWeight = DictGetVecDouble(user_info, "weights");
  mSpotEnergy = DictGetVecDouble(user_info, "energies");
  mSigmaEnergy = DictGetVecDouble(user_info, "energy_sigmas");
  mPhSpaceX = DictGetVecofVecDouble(user_info, "partPhSp_xV");
  mPhSpaceY = DictGetVecofVecDouble(user_info, "partPhSp_yV");

  mSpotPosition = DictGetVecG4ThreeVector(user_info, "positions");
  mSpotRotation = DictGetVecG4RotationMatrix(user_info, "rotations");

  mTotalNumberOfSpots = mNbIonsToGenerate.size();
}

// void GateTreatmentPlanSource::GeneratePrimaries(G4Event *event,
//                                           double current_simulation_time) {
//
//   if(mSortedSpotGenerationFlag){
//     while ( (mCurrentSpot<mTotalNumberOfSpots) &&
//     (mNbIonsToGenerate[mCurrentSpot] <= 0) ){
//       //GateMessage("Beam", 4, "[TPSPencilBeam] spot " << mCurrentSpot << "
//       has no ions left to generate." << Gateendl ); mCurrentSpot++;
//       need_pencilbeam_config = true;
//     }
//     if ( mCurrentSpot>=mTotalNumberOfSpots ){
//       GateError("Too many primary vertex requests!");
//     }
//   } else {
//     int nextspot = mTotalNumberOfSpots * mDistriGeneral->fire();
//     need_pencilbeam_config = (nextspot!=mCurrentSpot);
//     GateMessage("Beam", 5, "[TPSPencilBeam] hopping from spot " <<
//     mCurrentSpot << " to spot " << nextspot << Gateendl ); mCurrentSpot =
//     nextspot;
//   }
//   if ( need_pencilbeam_config ){
//     GateMessage("Beam", 5, "[TPSPencilBeam] mCurrentSpot = " << mCurrentSpot
//     << Gateendl ); ConfigurePencilBeam();
//   }
//   mPencilBeam->GenerateVertex(aEvent);
//   if (mSortedSpotGenerationFlag){
//     --mNbIonsToGenerate[mCurrentSpot];
//   }
// }

double
GateTreatmentPlanPBSource::PrepareNextTime(double current_simulation_time) {
  // If all N events have been generated, we stop (negative time)
  if (fNumberOfGeneratedEvents >= fMaxN) {
    return -1;
  }
  // Else we consider all event with a timestamp equal to the simulation
  // StartTime
  return fStartTime;
}

void GateTreatmentPlanPBSource::PrepareNextRun() {
  // The following compute the global transformation from
  // the local volume (mother) to the world
  GateVSource::PrepareNextRun();
  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
}

void GateTreatmentPlanPBSource::GeneratePrimaries(
    G4Event *event, double current_simulation_time) {
  // Find next spot to initialize
  if (mSortedSpotGenerationFlag) {
    // move to next spot if there are no more particles to generate in the
    // current one
    if ((mCurrentSpot < mTotalNumberOfSpots) &&
        (mNbIonsToGenerate[mCurrentSpot] == 0)) {
      mCurrentSpot++;
    }
  }
  if (mCurrentSpot >= mTotalNumberOfSpots) {
    Fatal("Too many primary vertex requests!");
  }
  // if we moved to a new spot, we need to update the SPS parmaeters
  if (mCurrentSpot != mPreviousSpot) {
    ConfigureSingleSpot();
  }

  // Generate vertex
  fSPS_PB->SetParticleTime(current_simulation_time);
  fSPS_PB->GeneratePrimaryVertex(event);

  // weight
  double w = mSpotWeight[mCurrentSpot];
  for (auto i = 0; i < event->GetNumberOfPrimaryVertex(); i++) {
    event->GetPrimaryVertex(i)->SetWeight(w);
  }

  // update previous spot
  mPreviousSpot = mCurrentSpot;

  // update number of generated events
  fNumberOfGeneratedEvents++;
  mNbIonsToGenerate[mCurrentSpot]--;
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
  double energy = mSpotEnergy[mCurrentSpot];
  double sigmaE = mSigmaEnergy[mCurrentSpot];
  UpdateEnergySPS(energy, sigmaE);

  // rotation and translation
  G4ThreeVector translation = mSpotPosition[mCurrentSpot];
  G4RotationMatrix rotation = mSpotRotation[mCurrentSpot];
  UpdatePositionSPS(translation, rotation);

  // Phase space parameters
  std::vector<double> x_param = mPhSpaceX[mCurrentSpot];
  std::vector<double> y_param = mPhSpaceY[mCurrentSpot];
  fSPS_PB->SetPBSourceParam(x_param, y_param);
}

void GateTreatmentPlanPBSource::UpdatePositionSPS(G4ThreeVector localTransl,
                                                  G4RotationMatrix localRot) {
  //   auto *pos = fSPS_PB->GetPosDist();
  //   // pos_type = "disc";
  //   pos->SetPosDisType("Beam");
  //   pos->SetPosDisShape("Circle");
  //   // radius for sphere, disc, cylinder
  //   pos->SetRadius(0.0);
  //   // gaussian sigma for disc
  //   pos->SetBeamSigmaInX(0.0);
  //   pos->SetBeamSigmaInY(0.0);

  // update local translation and rotation
  auto &l = fThreadLocalData.Get();
  fLocalTranslation = localTransl;
  fLocalRotation = localRot; // ConvertToG4RotationMatrix(localRot);

  // update global rotation
  GateVSource::SetOrientationAccordingToMotherVolume();

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
