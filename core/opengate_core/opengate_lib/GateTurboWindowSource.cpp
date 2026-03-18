#include "GateTurboWindowSource.h"
// #include "GateSourceTurboMessenger.hh"
#include <G4Event.hh>
#include "GateVoxelizedPosDistribution.hh"
#include "GateRandomEngine.hh"

G4bool GateSourceTurbo::random_engine_initialized = false;

G4int GateSourceTurbo::GeneratePrimaries(G4Event *event) {
  if (event)
    GateMessage("Beam", 2,
                "Generating particle " << event->GetEventID() << G4endl);

  G4int numVertices = 0;

  SetParticleTime(m_time);
  GeneratePrimaryVertex(event);
  numVertices++;

  // if (event) {
  //   for (int i = 0; i < event->GetPrimaryVertex(0)->GetNumberOfParticle();
  //        i++) {
  //     G4PrimaryParticle *p = event->GetPrimaryVertex(0)->GetPrimary(i);
  //     GateMessage("Beam", 3,
  //                 "(" << event->GetEventID() << ") "
  //                     << p->GetG4code()->GetParticleName()
  //                     << " pos=" << event->GetPrimaryVertex(0)->GetPosition()
  //                     << " weight=" << p->GetWeight()
  //                     << " energy=" << G4BestUnit(mEnergy, "Energy")
  //                     << " mom=" << p->GetMomentum()
  //                     << " ptime=" << G4BestUnit(p->GetProperTime(), "Time")
  //                     << " atime=" << G4BestUnit(GetTime(), "Time") <<
  //                     ")\n");
  //   }
  // }

  // if (event) {
  //   printf("time %e ns\n", GetTime());
  // }

  // G4cout<<"Generate primaries\n";
  return numVertices;
}

GateSourceTurbo::GateSourceTurbo(G4String name) : GateVSource(name) {
  m_sourceMessenger = new GateSourceTurboMessenger(this);
}
G4bool GateSourceTurbo::CheckPosDirValid(const G4ThreeVector &pos,
                                         const G4ThreeVector &dir) const {
  // compare theta with cos2, to avoid complex calculation
  //   G4double cot2theta = std::copysign(1.0, dir.z()) * dir.z() * dir.z() /
  //                        (dir.x() * dir.x() + dir.y() * dir.y());

  G4double x0 = pos.x() * cos_plane_phi + pos.y() * sin_plane_phi;
  G4double y0 = -pos.x() * sin_plane_phi + pos.y() * cos_plane_phi;
  G4double a1_rel = a1 - y0;
  G4double a2_rel = a2 - y0;
  G4double b1_rel = b1 - pos.z();
  G4double b2_rel = b2 - pos.z();
  G4double d_rel = plane_distance - x0;
  G4double dir_x_rotated = dir.x() * cos_plane_phi + dir.y() * sin_plane_phi;
  G4double dir_y_rotated = -dir.x() * sin_plane_phi + dir.y() * cos_plane_phi;

  G4double intersect_b = d_rel / dir_x_rotated * dir.z() + pos.z();
  G4double intersect_a = d_rel / dir_x_rotated * dir_y_rotated + y0;
  return intersect_a <= a2 && intersect_a >= a1 && intersect_b <= b2 &&
         intersect_b >= b1;
}

void verify_one(const G4ThreeVector start, const G4ThreeVector end, G4double theta_max, 
  G4double theta_min, G4double phi_max, G4double phi_min) {
  G4ThreeVector dir = end - start;
  G4double theta = M_PI-acos(dir.z() / dir.mag());
  G4double epsilon = 1e-10;
  G4double phi = atan2(dir.y(), dir.x())+M_PI;
  G4bool theta_valid = theta <= theta_max+epsilon && theta >= theta_min-epsilon;
  G4bool phi_valid = phi <= phi_max+epsilon && phi >= phi_min-epsilon;
  G4bool phi_valid_p2pi = phi+2*M_PI <= phi_max+epsilon && phi+2*M_PI >= phi_min-epsilon;
  if (!theta_valid || (!phi_valid && !phi_valid_p2pi)) {
    G4cerr << (theta>theta_max+epsilon)<< (theta<theta_min-epsilon)<< (phi>phi_max+epsilon)<< (phi<phi_min-epsilon)<< G4endl;
    G4cerr << "pos at " << start << " end at " << end << " theta " << theta << " phi " << phi << G4endl;
    fprintf(stderr, "theta %0.53lf\n phi %0.53lf\n", theta, phi);
    G4cerr << "pos up at" << start + G4ThreeVector(0, 0, 100) << " pos down at " << start + G4ThreeVector(0, 0, -100) << G4endl;
    G4cerr << "max theta radius is " << 100*tan(theta_max) << " min theta radius is " << 100*tan(theta_min) << G4endl;
    fprintf(stderr, "max theta+epsilon %0.53lf\n min theta-epsilon %0.53lf\n", theta_max+epsilon, theta_min-epsilon);
    fprintf(stderr, "max phi+epsilon %0.53lf\n min phi-epsilon %0.53lf\n", phi_max+epsilon, phi_min-epsilon);
    // G4cerr << "theta_max " << theta_max << " theta_min " << theta_min << " phi_max " << phi_max << " phi_min " << phi_min << G4endl;
    fflush(stderr);
    G4Exception("GateSourceTurbo::VerifyPhiTheta", "VerifyPhiThetaError",
                FatalException, "phi or theta not in range");

  }
    return;
}

void GateSourceTurbo::VerifyPhiTheta(G4int number_pos, G4double interval) const {
  G4ThreeVector pos;
  G4ThreeVector window_vt1, window_vt2, window_vt3, window_vt4;
  GetWindowVertex(window_vt1, window_vt2, window_vt3, window_vt4);
  G4ThreeVector delta12 = window_vt2 - window_vt1;
  G4ThreeVector norm12 = delta12.unit();
  G4double num_interval_12 = delta12.mag() / interval;
  G4ThreeVector delta13 = window_vt3 - window_vt1;
  G4ThreeVector norm13 = delta13.unit();
  G4double num_interval_13 = delta13.mag() / interval;
  G4cout << "plane distancce" << plane_distance << " plane_phi " << plane_phi <<G4endl;
  G4cout << "a1 " << a1 << " a2 " << a2 << " b1 " << b1 << " b2 " << b2 << G4endl;
  G4cout <<"window vertexs: "<<window_vt1 << " " << window_vt2 << " " << window_vt3 << " " << window_vt4 << G4endl;
  for (G4int i = 0; i < number_pos; i++) {
    pos = m_posSPS->GenerateOne();
    SetPhiTheta(pos);
    G4double theta_max = m_angSPS->GetMaxTheta();
    G4double theta_min = m_angSPS->GetMinTheta();
    G4double phi_max = m_angSPS->GetMaxPhi();
    G4double phi_min = m_angSPS->GetMinPhi();
    for (G4int j = 0; j < num_interval_12; j++)
    {
      G4ThreeVector end = window_vt1 + norm12 * interval * j;
      verify_one(pos, end, theta_max, theta_min, phi_max, phi_min);
      end = window_vt3 + norm12 * interval * j;
      verify_one(pos, end, theta_max, theta_min, phi_max, phi_min);
    }
    for (G4int j = 0; j < num_interval_13; j++)
    {
      G4ThreeVector end = window_vt1 + norm13 * interval * j;
      verify_one(pos, end, theta_max, theta_min, phi_max, phi_min);
      end = window_vt2 + norm13 * interval * j;
      verify_one(pos, end, theta_max, theta_min, phi_max, phi_min);
    }
  }
  G4cout << "VerifyPhiTheta passed for " << number_pos << " positions" << G4endl;
}

void GateSourceTurbo::SetPhiTheta(const G4ThreeVector &pos) const {
  // compare theta with cos2, to avoid complex calculation
  //   G4double cot2theta = std::copysign(1.0, dir.z()) * dir.z() * dir.z() /
  //                        (dir.x() * dir.x() + dir.y() * dir.y());
  // relationship between angular vector and theta and phi in Geant4
  // px = -sintheta * cosphi;
  // py = -sintheta * sinphi;
  // pz = -costheta;

  G4double x0 = pos.x() * cos_plane_phi + pos.y() * sin_plane_phi;
  G4double y0 = -pos.x() * sin_plane_phi + pos.y() * cos_plane_phi;
  G4double a1_rel = a1 - y0;
  G4double a2_rel = a2 - y0;
  G4double b1_rel = b1 - pos.z();
  G4double b2_rel = b2 - pos.z();
  G4double d_rel = plane_distance - x0;

  G4double aamax = std::max(a1_rel * a1_rel, a2_rel * a2_rel);
  G4double aamin = std::min(a1_rel * a1_rel, a2_rel * a2_rel);
  G4double thetamax, thetamin;

  if (a1_rel < 0 and a2_rel > 0 and b2_rel > 0)
    thetamax = M_PI-atan2(d_rel,b2_rel);
  else
    thetamax = M_PI-atan2(sqrt((b2_rel > 0 ? aamin : aamax) + d_rel * d_rel), b2_rel);

  if (a1_rel < 0 and a2_rel > 0 and b1_rel < 0)
    // in this case, need to check minmum/maxmum of the hyperbola 
    thetamin = M_PI-atan2(d_rel,b1_rel);
  else
    thetamin = M_PI-atan2(sqrt((b1_rel > 0 ? aamax : aamin) + d_rel * d_rel), b1_rel);

  m_angSPS->SetMinTheta(thetamin);
  m_angSPS->SetMaxTheta(thetamax);
  G4double phimin = atan2(a1_rel, d_rel) + plane_phi;
  G4double phimax = atan2(a2_rel, d_rel) + plane_phi;

  m_angSPS->SetMinPhi(phimin+M_PI);
  m_angSPS->SetMaxPhi(phimax+M_PI);
}

G4double solid_angle_pyramid(G4double a, G4double b, G4double d) {
  return 4 * atan(a * b / (2 * d * sqrt(a * a + b * b + 4 * d * d)));
}

G4double GateSourceTurbo::GetSolidAngle(const G4ThreeVector &pos) const {
  // if (pos.mag2() >= mPth1.mag2() || pos.mag2() >= mPth2.mag2() ||
  //     pos.mag2() >= mPphi1.mag2() || pos.mag2() >= mPphi2.mag2()) {
  //   G4Exception("GateSourceTurbo::GetSolidAngle", "GetSolidAngleError",
  //               FatalException, "source position not inside edge point");
  // }

  // rotate with -plane_phi

  G4double x0 = pos.x() * cos_plane_phi + pos.y() * sin_plane_phi;
  G4double y0 = -pos.x() * sin_plane_phi + pos.y() * cos_plane_phi;
  G4double a1_rel = a1 - y0;
  G4double a2_rel = a2 - y0;
  G4double b1_rel = b1 - pos.z();
  G4double b2_rel = b2 - pos.z();
  G4double d_rel = plane_distance - x0;
  G4double sa11 = solid_angle_pyramid(2 * a1_rel, 2 * b1_rel, d_rel);
  G4double sa12 = solid_angle_pyramid(2 * a1_rel, 2 * b2_rel, d_rel);
  G4double sa21 = solid_angle_pyramid(2 * a2_rel, 2 * b1_rel, d_rel);
  G4double sa22 = solid_angle_pyramid(2 * a2_rel, 2 * b2_rel, d_rel);
  G4double sa = sa11 + sa22 - sa12 - sa21;
  return fabs(sa * 0.25);
}

void GateSourceTurbo::Initialize(G4int samplingCount) {
  
  GateRandomEngine* theRandomEngine = GateRandomEngine::GetInstance();
  if (!random_engine_initialized) {
    theRandomEngine->Initialize();
    random_engine_initialized = true;
  }
  if (a1 != a1 || a2 != a2 || b1 != b1 || b2 != b2 ||
      plane_distance != plane_distance || plane_phi != plane_phi) {
    G4Exception("GateSourceTurbo::SetActRatio", "SetActRatioError",
                FatalException, "Not all parameters needed points are set");
  }

  if (a1 >= a2 || b1 >= b2) {
    G4Exception("GateSourceTurbo::SetActRatio", "SetActRatioError",
                FatalException, "a1 >= a2 or b1 >= b2");
  }
  GateVVolume *v = mVolume;
  if (v == nullptr) 
  {
    SetRelativePlacementVolume("world");
    v = mVolume;
  }
  while (v->GetObjectName() != "world") {

    if (G4RotationMatrix({{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}) !=
        v->GetPhysicalVolume(0)->GetObjectRotationValue()) {
      G4Exception("GateSourceTurbo::SetActRatio", "SetActRatioError",
                  FatalException,
                  "Turbo source must not attach to a rotated volume");
    }
    v = v->GetParentVolume();
  }
  auto start_time = std::chrono::high_resolution_clock::now();
  G4double act_ratio_all = 0;
  G4ThreeVector pos;
  for (G4int i = 0; i < samplingCount; i++) {
    pos = m_posSPS->GenerateOne();
    G4double solid_angle = GetSolidAngle(pos);
    if (solid_angle > max_solid_angle) 
      max_solid_angle = solid_angle;
    act_ratio_all += solid_angle / 4 / M_PI;
  }
  act_ratio = act_ratio_all / samplingCount;
  act_ratio_set = true;
  max_solid_angle_set = true;
  auto end_time = std::chrono::high_resolution_clock::now();
  auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
      end_time - start_time);
  G4cout << "Activity Ratio of source " << m_name << " is " << std::scientific 
         << std::setprecision(10) << act_ratio << std::defaultfloat << G4endl;
  G4cout << "Max Solid Angle of source " << m_name << " is " << std::scientific 
         << std::setprecision(10) << max_solid_angle<< std::defaultfloat << G4endl;
  if (nVerboseLevel > 0)
    G4cout << "Time used: " << duration.count() << " microseconds" << G4endl;
  // VerifyPhiTheta(samplingCount, 0.01);
}

void GateSourceTurbo::GeneratePrimaryVertex(G4Event *event) {
  if (not (act_ratio_set and max_solid_angle_set)) {
    G4String error_msg = "activity ratio or max solid angle not set for source: ";
    error_msg += m_name;
    G4Exception("GateSourceTurbo::GeneratePrimaryVertex",
                "GeneratePrimaryVertexError", FatalException,
                error_msg);
  }
  G4ThreeVector position = m_posSPS->GenerateOne();

  //probability of the position is valid should be proportional to the solid angle
  while (true) {
    G4double solid_angle = GetSolidAngle(position);
    if (solid_angle > max_solid_angle * 1.1) {
      G4String error_msg = "solid angle of position is larger than max solid angle for source: ";
      error_msg += m_name;
      error_msg += "\nyou may increase max solid angle and try again";
      G4Exception("GateSourceTurbo::GeneratePrimaryVertex",
                  "GeneratePrimaryVertexError", FatalException,
                  error_msg);
    }
    if (G4UniformRand() < solid_angle / max_solid_angle / 1.1) {
      break;
    }
    position = m_posSPS->GenerateOne();
  }

  ChangeParticlePositionRelativeToAttachedVolume(position);
  SetPhiTheta(position);
  G4ThreeVector direction;
  while (true) {
    direction = m_angSPS->GenerateOne();
    if (CheckPosDirValid(position, direction)) {
      break;
    }
  }
  G4PrimaryVertex *vertex = new G4PrimaryVertex(position, GetParticleTime());

  // Set placement relative to attached volume
  // DD(particle_momentum_direction);

  G4double particle_energy = 0;
  particle_energy = m_eneSPS->GenerateOne(GetParticleDefinition());
  mEnergy = particle_energy; // because particle_energy is private

  G4double mass = GetParticleDefinition()->GetPDGMass();
  G4double energy = particle_energy + mass;
  G4double pmom = std::sqrt(energy * energy - mass * mass);
  G4double px = pmom * direction.x();
  G4double py = pmom * direction.y();
  G4double pz = pmom * direction.z();

  G4PrimaryParticle *particle =
      new G4PrimaryParticle(GetParticleDefinition(), px, py, pz);
  particle->SetMass(mass);
  particle->SetCharge(GetParticleDefinition()->GetPDGCharge());
  particle->SetPolarization(GetParticlePolarization().x(),
                            GetParticlePolarization().y(),
                            GetParticlePolarization().z());

  G4double particle_weight = GetBiasRndm()->GetBiasWeight();
  particle->SetWeight(particle_weight);

  // Add one particle
  vertex->SetPrimary(particle);

  // Verbose
  if (nVerboseLevel > 1) {
    G4cout << "Particle name: " << GetParticleDefinition()->GetParticleName()
           << G4endl;
    G4cout << "       Energy: " << particle_energy << G4endl;
    G4cout << "     Position: " << particle_position << G4endl;
    G4cout << "    Direction: " << direction << G4endl;
  }
  if (nVerboseLevel > 2) {
    G4cout << "Creating primaries and assigning to vertex\n";
  }

  event->AddPrimaryVertex(vertex);
}

G4double GateSourceTurbo::GetNextTime(G4double timeStart) {

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


void GateSourceTurbo::LoadVoxelizedPhantom(G4String filename)
{
  if(m_posSPS)
    delete m_posSPS;
  m_posSPS = new GateVoxelizedPosDistribution(filename);
  m_angSPS->SetPosDistribution(m_posSPS);

}

void GateSourceTurbo::SetPhantomPosition(G4ThreeVector pos)
{
  GateVoxelizedPosDistribution* posDist = dynamic_cast<GateVoxelizedPosDistribution*>(m_posSPS);
  if(posDist)
    posDist->SetPosition(pos);
  else
    G4cout << "Can't use this command unless a voxelized phantom has already been loaded." << G4endl;

}

void GateSourceTurbo::GetWindowVertex(G4ThreeVector &pos1, G4ThreeVector &pos2, G4ThreeVector &pos3, G4ThreeVector &pos4) const {
  pos1 = {plane_distance, a1, b1};
  pos2 = {plane_distance, a1, b2};
  pos3 = {plane_distance, a2, b1};
  pos4 = {plane_distance, a2, b2};
  //rotate with plane_phi
  G4double s = sin_plane_phi;
  G4double c = cos_plane_phi;
  G4RotationMatrix rot({{c, s, 0}, {-s, c, 0}, {0, 0, 1}});
  pos1 = rot * pos1;
  pos2 = rot * pos2;
  pos3 = rot * pos3;
  pos4 = rot * pos4;
}