// TODO: 需要自行清除 ang->fGlobalRotation，如果
// 复用GateGenericSource::PrepareNextRun()的话
// 每个线程各算各的粒子数
#include "GateWindowTurboSource.h"
#include "GateHelpersDict.h"
#include "GateSingleParticleSourceWindowTurbo.h"
#include "GateVSource.h"
#include <G4Event.hh>
#include <Randomize.hh>

// G4bool GateWindowTurboSource::random_engine_initialized = false;

void GateWindowTurboSource::CreateSPS() {
  auto &ll = GetThreadLocalDataGenericSource();
  ll.fSPS = new GateSingleParticleSourceWindowTurbo(fAttachedToVolumeName);
}

void GateWindowTurboSource::InitializeUserInfo(py::dict &user_info) {
  GateGenericSource::InitializeUserInfo(user_info);
  // TBD: should these be addressed in python side?
  auto &ll = GetThreadLocalDataGenericSource();
  fSkip = DictGetBool(user_info, "skip_mode");
  GateSingleParticleSourceWindowTurbo *sps =
      reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(ll.fSPS);
  sps->SetSkipMode(fSkip);
  fWeight = -1;
  fWeightSigma = -1;
  fDirectionRelativeToAttachedVolume = false;
}

// TBD: override update TAC?

double GateWindowTurboSource::CalcNextTime(double current_simulation_time) {
  GateSingleParticleSourceWindowTurbo *sps =
      reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(
          GetThreadLocalDataGenericSource().fSPS);
  G4double act_ratio;
  if (fSkip) {
    if (not sps->GetPosGenerated()) {
      sps->GeneratePos();
    }
    act_ratio = sps->GetCurrentSolidAngle() / (4 * M_PI);
  } else
    act_ratio = sps->GetActRatio();

  double next_time = current_simulation_time;
  if ((fMaxN <= 0)) {
    next_time = current_simulation_time -
                log(G4UniformRand()) * (1.0 / fActivity / act_ratio);
  }
  return next_time;
}

void GateWindowTurboSource::PrepareNextRun() {
  GateGenericSource::PrepareNextRun();
  // TBD: voxelized source prepare next run here
  auto &ll = GetThreadLocalDataGenericSource();
  auto *ang = ll.fSPS->GetAngDist();
  ang->fGlobalRotation = G4RotationMatrix();
  // since the azumuthal and elevation angles are controlled later
  // TBD: Should the initialization for sps be done again here? most likely yes
}

void GateWindowTurboSource::GeneratePrimaries(
    G4Event *event, const double current_simulation_time) {
  GateGenericSource::GeneratePrimaries(event, current_simulation_time);
  // auto &ll = GetThreadLocalDataGenericSource();
  // GateSingleParticleSourceWindowTurbo *sps =
  //     reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(ll.fSPS);
  // if (fSkip) {
  //   G4double current_solid_angle = sps->GetCurrentSolidAngle();
  //   ll.fCurrentSkippedEvents += 4 * M_PI / current_solid_angle - 1;
  //   ll.fEffectiveEventTime +=
  //       G4RandGamma::shoot(ll.fCurrentSkippedEvents, fActivity);
  // }
  // TODO:finish this
}

void GateWindowTurboSource::InitializeDirection(py::dict puser_info) {
  auto &ll = fThreadLocalDataGenericSource.Get();
  auto *ang = ll.fSPS->GetAngDist();
  ang->SetAngDistType("iso");
  auto user_info = py::dict(puser_info["direction"]);
  GateSingleParticleSourceWindowTurbo *sps =
      reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(ll.fSPS);
  sps->Initialize(user_info, fName);
  if (ll.fAAManager == nullptr) {
    ll.fAAManager = new GateAcceptanceAngleManager;
    ll.fSPS->SetAAManager(ll.fAAManager);
  }
  if (ll.fFDManager == nullptr) {
    ll.fFDManager = new GateForcedDirectionManager;
    ll.fSPS->SetFDManager(ll.fFDManager);
  }
}

// void verify_one(const G4ThreeVector start, const G4ThreeVector end,
//                 G4double theta_max, G4double theta_min, G4double phi_max,
//                 G4double phi_min) {
//   G4ThreeVector dir = end - start;
//   G4double theta = M_PI - acos(dir.z() / dir.mag());
//   G4double epsilon = 1e-10;
//   G4double phi = atan2(dir.y(), dir.x()) + M_PI;
//   G4bool theta_valid =
//       theta <= theta_max + epsilon && theta >= theta_min - epsilon;
//   G4bool phi_valid = phi <= phi_max + epsilon && phi >= phi_min - epsilon;
//   G4bool phi_valid_p2pi = phi + 2 * M_PI <= phi_max + epsilon &&
//                           phi + 2 * M_PI >= phi_min - epsilon;
//   if (!theta_valid || (!phi_valid && !phi_valid_p2pi)) {
//     G4cerr << (theta > theta_max + epsilon) << (theta < theta_min - epsilon)
//            << (phi > phi_max + epsilon) << (phi < phi_min - epsilon) <<
//            G4endl;
//     G4cerr << "pos at " << start << " end at " << end << " theta " << theta
//            << " phi " << phi << G4endl;
//     fprintf(stderr, "theta %0.53lf\n phi %0.53lf\n", theta, phi);
//     G4cerr << "pos up at" << start + G4ThreeVector(0, 0, 100) << " pos down
//     at "
//            << start + G4ThreeVector(0, 0, -100) << G4endl;
//     G4cerr << "max theta radius is " << 100 * tan(theta_max)
//            << " min theta radius is " << 100 * tan(theta_min) << G4endl;
//     fprintf(stderr, "max theta+epsilon %0.53lf\n min theta-epsilon
//     %0.53lf\n",
//             theta_max + epsilon, theta_min - epsilon);
//     fprintf(stderr, "max phi+epsilon %0.53lf\n min phi-epsilon %0.53lf\n",
//             phi_max + epsilon, phi_min - epsilon);
//     // G4cerr << "theta_max " << theta_max << " theta_min " << theta_min << "
//     // phi_max " << phi_max << " phi_min " << phi_min << G4endl;
//     fflush(stderr);
//     G4Exception("GateWindowTurboSource::VerifyPhiTheta",
//     "VerifyPhiThetaError",
//                 FatalException, "phi or theta not in range");
//   }
//   return;
// }

// void GateWindowTurboSource::VerifyPhiTheta(G4int number_pos,
//                                            G4double interval) const {
//   G4ThreeVector pos;
//   G4ThreeVector window_vt1, window_vt2, window_vt3, window_vt4;
//   GetWindowVertex(window_vt1, window_vt2, window_vt3, window_vt4);
//   G4ThreeVector delta12 = window_vt2 - window_vt1;
//   G4ThreeVector norm12 = delta12.unit();
//   G4double num_interval_12 = delta12.mag() / interval;
//   G4ThreeVector delta13 = window_vt3 - window_vt1;
//   G4ThreeVector norm13 = delta13.unit();
//   G4double num_interval_13 = delta13.mag() / interval;
//   G4cout << "plane distancce" << plane_distance << " plane_phi " << plane_phi
//          << G4endl;
//   G4cout << "a1 " << a1 << " a2 " << a2 << " b1 " << b1 << " b2 " << b2
//          << G4endl;
//   G4cout << "window vertexs: " << window_vt1 << " " << window_vt2 << " "
//          << window_vt3 << " " << window_vt4 << G4endl;
//   for (G4int i = 0; i < number_pos; i++) {
//     pos = m_posSPS->GenerateOne();
//     SetPhiTheta(pos);
//     G4double theta_max = m_angSPS->GetMaxTheta();
//     G4double theta_min = m_angSPS->GetMinTheta();
//     G4double phi_max = m_angSPS->GetMaxPhi();
//     G4double phi_min = m_angSPS->GetMinPhi();
//     for (G4int j = 0; j < num_interval_12; j++) {
//       G4ThreeVector end = window_vt1 + norm12 * interval * j;
//       verify_one(pos, end, theta_max, theta_min, phi_max, phi_min);
//       end = window_vt3 + norm12 * interval * j;
//       verify_one(pos, end, theta_max, theta_min, phi_max, phi_min);
//     }
//     for (G4int j = 0; j < num_interval_13; j++) {
//       G4ThreeVector end = window_vt1 + norm13 * interval * j;
//       verify_one(pos, end, theta_max, theta_min, phi_max, phi_min);
//       end = window_vt2 + norm13 * interval * j;
//       verify_one(pos, end, theta_max, theta_min, phi_max, phi_min);
//     }
//   }
//   G4cout << "VerifyPhiTheta passed for " << number_pos << " positions"
//          << G4endl;
// }

// void GateWindowTurboSource::CheckMotherVolumeIsNotRotated() const {
// TODO: reimplement
//  GateVVolume *v = mVolume;
//  if (v == nullptr) {
//    SetRelativePlacementVolume("world");
//    v = mVolume;
//  }
//  while (v->GetObjectName() != "world") {

//   if (G4RotationMatrix({{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}) !=
//       v->GetPhysicalVolume(0)->GetObjectRotationValue()) {
//     G4Exception("GateWindowTurboSource::SetActRatio", "SetActRatioError",
//                 FatalException,
//                 "Turbo source must not attach to a rotated volume");
//   }
//   v = v->GetParentVolume();
// }
// }

G4double GateWindowTurboSource::GetNextTime(G4double timeStart) {

  /* GetVolumeID ??? */

  // returns the proposed time for the next event of this source, sampled from
  // the source time distribution
  G4double aTime = DBL_MAX;

  // if(m_activity==0 && m_timeInterval!=0.)  SetActivity();

  if (m_activity > 0.) {
    // compute the present activity, on the base of the starting activity and
    // the lifetime (if any)
    G4double activityNow = m_activity;
    if (timeStart < m_startTime)
      activityNow = 0.;
    else {
      // Force life time to 0, time is managed by GATE not G4
      GetParticleDefinition()->SetPDGLifeTime(0);
      if (m_forcedUnstableFlag) {
        if (m_forcedLifeTime > 0.) {
          activityNow =
              m_activity * exp(-(timeStart - m_startTime) / m_forcedLifeTime);
        } else {
          G4cout << "[GateVSource::GetNextTime] ERROR: Forced decay with "
                    "negative lifetime: (s) "
                 << m_forcedLifeTime / s << G4endl;
        }
      } else {
        G4ParticleDefinition *partDef = GetParticleDefinition();
        if (partDef) {
          if (!(partDef->GetPDGStable())) {
            if (nVerboseLevel > 0)
              G4cout << "GateVSource::GetNextTime : unstable particle "
                     << GetParticleDefinition()->GetParticleName()
                     << " from source " << GetName() << G4endl;
            // activity is constant
            activityNow = m_activity;
          } else if (nVerboseLevel > 1)
            G4cout << "GateVSource::GetNextTime : stable particle "
                   << GetParticleDefinition()->GetParticleName()
                   << " from source " << GetName() << G4endl;
        } else if (nVerboseLevel > 0)
          G4cout << "GateVSource::GetNextTime : NULL ParticleDefinition for "
                    "source "
                 << GetName() << " assumed stable \n";
      }
    }

    activityNow *= act_ratio;

    if (nVerboseLevel > 0)
      G4cout << "GateVSource::GetNextTime : Initial activity (becq) : "
             << m_activity / becquerel << G4endl
             << "                            At time (s) " << timeStart / s
             << " activity (becq) " << activityNow / becquerel << G4endl;

    // sampling of the interval distribution
    if (!mEnableRegularActivity) {
      aTime = -log(G4UniformRand()) * (1. / activityNow);
    } else {
      GateError("I should not be here. ");
      // DD(activityNow);
      //         DD(m_activity);
      //         DD(timeStart/s);
      aTime = 1. / activityNow;
    }
  }

  if (nVerboseLevel > 0)
    G4cout << "GateVSource::GetNextTime : next time (s) " << aTime / s
           << G4endl;

  // Dump(0);
  /*G4cout<< "    CentreCoords       (mm)  : "
               << m_posSPS->GetCentreCoords().x()/mm << " "
               << m_posSPS->GetCentreCoords().y()/mm << " "
               << m_posSPS->GetCentreCoords().z()/mm << G4endl;*/
  return aTime;
}

void GateWindowTurboSource::LoadVoxelizedPhantom(G4String filename) {
  if (m_posSPS)
    delete m_posSPS;
  m_posSPS = new GateVoxelizedPosDistribution(filename);
  m_angSPS->SetPosDistribution(m_posSPS);
}

void GateWindowTurboSource::SetPhantomPosition(G4ThreeVector pos) {
  GateVoxelizedPosDistribution *posDist =
      dynamic_cast<GateVoxelizedPosDistribution *>(m_posSPS);
  if (posDist)
    posDist->SetPosition(pos);
  else
    G4cout << "Can't use this command unless a voxelized phantom has already "
              "been loaded."
           << G4endl;
}

void GateWindowTurboSource::GetWindowVertex(G4ThreeVector &pos1,
                                            G4ThreeVector &pos2,
                                            G4ThreeVector &pos3,
                                            G4ThreeVector &pos4) const {
  pos1 = {plane_distance, a1, b1};
  pos2 = {plane_distance, a1, b2};
  pos3 = {plane_distance, a2, b1};
  pos4 = {plane_distance, a2, b2};
  // rotate with plane_phi
  G4double s = sin_plane_phi;
  G4double c = cos_plane_phi;
  G4RotationMatrix rot({{c, s, 0}, {-s, c, 0}, {0, 0, 1}});
  pos1 = rot * pos1;
  pos2 = rot * pos2;
  pos3 = rot * pos3;
  pos4 = rot * pos4;
}
