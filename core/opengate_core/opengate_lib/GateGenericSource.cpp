/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGenericSource.h"
#include "G4IonTable.hh"
#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GateHelpersDict.h"
#include <G4UnitsTable.hh>

GateGenericSource::GateGenericSource() : GateVSource() {
  fNumberOfGeneratedEvents = 0;
  fMaxN = 0;
  fActivity = 0;
  fInitGenericIon = false;
  fA = 0;
  fZ = 0;
  fE = 0;
  fInitConfine = false;
  fWeight = -1;
  fWeightSigma = -1;
  fHalfLife = -1;
  fDecayConstant = -1;
  fTotalSkippedEvents = 0;
  fCurrentSkippedEvents = 0;
  fTotalZeroEvents = 0;
  fCurrentZeroEvents = 0;
  fSPS = nullptr;
  fInitialActivity = 0;
  fParticleDefinition = nullptr;
  fEffectiveEventTime = -1;
  fEffectiveEventTime = -1;
}

GateGenericSource::~GateGenericSource() {
  // FIXME: we cannot really delete fSPS and fAAManager
  // I dont know exactly why.
  // Maybe because it has been created in a thread which
  // can be different from the thread that delete.
  auto &l = fThreadLocalDataAA.Get();
  if (l.fAAManager != nullptr) {
    // delete l.fAAManager;
  }
  // delete fSPS;
}

void GateGenericSource::CleanWorkerThread() {
  // Not used yet. Maybe later to clean local data in a thread.
}

void GateGenericSource::CreateSPS() {
  fSPS = new GateSingleParticleSource(fMother);
}

void GateGenericSource::SetEnergyCDF(const std::vector<double> &cdf) {
  fEnergyCDF = cdf;
}

void GateGenericSource::SetProbabilityCDF(const std::vector<double> &cdf) {
  fProbabilityCDF = cdf;
}

void GateGenericSource::SetTAC(const std::vector<double> &times,
                               const std::vector<double> &activities) {
  fTAC_Times = times;
  fTAC_Activities = activities;
}

void GateGenericSource::InitializeUserInfo(py::dict &user_info) {
  GateVSource::InitializeUserInfo(user_info);
  CreateSPS();

  // get user info about activity or nb of events
  fMaxN = DictGetInt(user_info, "n");
  fActivity = DictGetDouble(user_info, "activity");
  fInitialActivity = fActivity;

  // half life ?
  fHalfLife = DictGetDouble(user_info, "half_life");
  fDecayConstant = log(2) / fHalfLife;
  fUserParticleLifeTime = DictGetDouble(user_info, "user_particle_life_time");

  // weight
  fWeight = DictGetDouble(user_info, "weight");
  fWeightSigma = DictGetDouble(user_info, "weight_sigma");

  // get the user info for the particle
  InitializeParticle(user_info);

  // position, direction, energy
  InitializePosition(user_info);
  InitializeDirection(user_info);
  InitializeEnergy(user_info);

  // FIXME todo polarization

  // init number of events
  fNumberOfGeneratedEvents = 0;
  fCurrentSkippedEvents = 0;
  fTotalSkippedEvents = 0;
  fEffectiveEventTime = -1;
}

void GateGenericSource::UpdateActivity(double time) {
  if (!fTAC_Times.empty())
    return UpdateActivityWithTAC(time);
  if (fHalfLife <= 0)
    return;
  fActivity = fInitialActivity * exp(-fDecayConstant * (time - fStartTime));
}

void GateGenericSource::UpdateActivityWithTAC(double time) {
  // Below/above the TAC ?
  if (time < fTAC_Times.front() || time > fTAC_Times.back()) {
    fActivity = 0;
    return;
  }

  // Search for the time bin
  auto lower = std::lower_bound(fTAC_Times.begin(), fTAC_Times.end(), time);
  auto i = std::distance(fTAC_Times.begin(), lower);

  // Last element ?
  if (i == fTAC_Times.size() - 1) {
    fActivity = fTAC_Activities.back();
    return;
  }

  // linear interpolation
  double bin_time = fTAC_Times[i + 1] - fTAC_Times[i];
  double w1 = (time - fTAC_Times[i]) / bin_time;
  double w2 = (fTAC_Times[i + 1] - time) / bin_time;
  fActivity = fTAC_Activities[i] * w1 + fTAC_Activities[i + 1] * w2;
}

double GateGenericSource::PrepareNextTime(double current_simulation_time) {
  // initialization of the effective event time (it can be in the
  // future according to the current_simulation_time)
  if (fEffectiveEventTime < current_simulation_time) {
    fEffectiveEventTime = current_simulation_time;
  }
  UpdateActivity(fEffectiveEventTime);

  fTotalSkippedEvents += fCurrentSkippedEvents;
  fTotalZeroEvents += fCurrentZeroEvents;
  fCurrentZeroEvents = 0;
  auto cse = fCurrentSkippedEvents;
  fCurrentSkippedEvents = 0;

  // if MaxN is below zero, we check the time
  if (fMaxN <= 0) {
    if (fEffectiveEventTime < fStartTime)
      return fStartTime;
    if (fEffectiveEventTime >= fEndTime)
      return -1;

    // get next time according to current fActivity
    double next_time =
        fEffectiveEventTime - log(G4UniformRand()) * (1.0 / fActivity);
    if (next_time >= fEndTime)
      return -1;
    return next_time;
  }

  // check according to t MaxN
  if (fNumberOfGeneratedEvents + cse >= fMaxN) {
    return -1;
  }
  return fStartTime;
}

void GateGenericSource::PrepareNextRun() {
  // The following compute the global transformation from
  // the local volume (mother) to the world
  GateVSource::PrepareNextRun();
  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
  auto &l = fThreadLocalData.Get();
  auto *pos = fSPS->GetPosDist();
  pos->SetCentreCoords(l.fGlobalTranslation);

  // orientation according to mother volume
  auto rotation = l.fGlobalRotation;
  G4ThreeVector r1(rotation(0, 0), rotation(0, 1), rotation(0, 2));
  G4ThreeVector r2(rotation(1, 0), rotation(1, 1), rotation(1, 2));
  pos->SetPosRot1(r1);
  pos->SetPosRot2(r2);
}

void GateGenericSource::UpdateEffectiveEventTime(
    double current_simulation_time, unsigned long skipped_particle) {
  unsigned long n = 0;
  fEffectiveEventTime = current_simulation_time;
  while (n < skipped_particle) {
    fEffectiveEventTime =
        fEffectiveEventTime - log(G4UniformRand()) * (1.0 / fActivity);
    n++;
  }
}

void GateGenericSource::GeneratePrimaries(G4Event *event,
                                          double current_simulation_time) {
  // Generic ion cannot be created at initialization.
  // It must be created the first time we get there
  if (fInitGenericIon) {
    auto *ion_table = G4IonTable::GetIonTable();
    auto *ion = ion_table->GetIon(fZ, fA, fE);
    fSPS->SetParticleDefinition(ion);
    SetLifeTime(ion);
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
  // (acceptance angle is included)
  fSPS->SetParticleTime(current_simulation_time);
  fSPS->GeneratePrimaryVertex(event);

  // update the time according to skipped events
  fEffectiveEventTime = current_simulation_time;
  auto &l = fThreadLocalDataAA.Get();
  if (l.fAAManager->IsEnabled()) {
    if (l.fAAManager->GetPolicy() ==
        GateAcceptanceAngleTesterManager::AASkipEvent) {
      UpdateEffectiveEventTime(current_simulation_time,
                               l.fAAManager->GetNumberOfNotAcceptedEvents());
      fCurrentSkippedEvents = l.fAAManager->GetNumberOfNotAcceptedEvents();
      event->GetPrimaryVertex(0)->SetT0(fEffectiveEventTime);
    } else {
      fCurrentZeroEvents =
          l.fAAManager->GetNumberOfNotAcceptedEvents(); // 1 or 0
    }
  }

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

void GateGenericSource::InitializeParticle(py::dict &user_info) {
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
  fSPS->SetParticleDefinition(fParticleDefinition);
  SetLifeTime(fParticleDefinition);
}

void GateGenericSource::InitializeIon(py::dict &user_info) {
  auto u = py::dict(user_info["ion"]);
  fA = DictGetInt(u, "A");
  fZ = DictGetInt(u, "Z");
  fE = DictGetDouble(u, "E");
  fInitGenericIon = true;
}

void GateGenericSource::InitializePosition(py::dict puser_info) {
  /* G4:
   * pos_types = ['Point', 'Beam', 'Plane', 'Surface', 'Volume']
   * shape_types = ['Square', 'Circle', 'Annulus', 'Ellipse', 'Rectangle',
                     'Sphere', 'Ellipsoid', 'Cylinder', 'Right', 'NULL']
  * New interface -> point box sphere disc (later: ellipse)
  * translation rotation size radius
  */
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
    pos->SetHalfZ(dz);
  }

  // radius for sphere, disc, cylinder
  auto radius = DictGetDouble(user_info, "radius");
  pos->SetRadius(radius);

  // gaussian sigma for disc
  auto sx = DictGetDouble(user_info, "sigma_x");
  pos->SetBeamSigmaInX(sx);
  auto sy = DictGetDouble(user_info, "sigma_y");
  pos->SetBeamSigmaInY(sy);

  // rotation
  auto rotation = DictGetMatrix(user_info, "rotation");

  // save local translation and rotation (will be used in
  // SetOrientationAccordingToMotherVolume)
  fLocalTranslation = translation;
  fLocalRotation = ConvertToG4RotationMatrix(rotation);

  // confine to a volume ?
  if (user_info.contains("confine")) {
    auto v = DictGetStr(user_info, "confine");
    if (v != "None") {
      fConfineVolume = v;
      fInitConfine = true;
    }
  }
}

void GateGenericSource::InitializeDirection(py::dict puser_info) {
  /*
   * G4: iso, cos, beam  and user for isotropic, cosine-law, beam and
   * user-defined
   *
   * New ones: iso, focus, direction
   * (Later: beam, user defined)
   */
  auto user_info = py::dict(puser_info["direction"]);
  auto *ang = fSPS->GetAngDist();
  auto ang_type = DictGetStr(user_info, "type");
  std::vector<std::string> ll = {"iso", "momentum", "focused",
                                 "beam2d"}; // FIXME check on py side ?
  CheckIsIn(ang_type, ll);
  if (ang_type == "iso") {
    ang->SetAngDistType("iso");
  }
  if (ang_type == "momentum") {
    ang->SetAngDistType("planar"); // FIXME really ??
    auto d = DictGetG4ThreeVector(user_info, "momentum");
    ang->SetParticleMomentumDirection(d);
  }
  if (ang_type == "focused") {
    ang->SetAngDistType("focused");
    auto f = DictGetG4ThreeVector(user_info, "focus_point");
    ang->SetFocusPoint(f);
  }
  if (ang_type == "beam2d") {
    ang->SetAngDistType("beam2d");
    auto sigma = DictGetVecDouble(user_info, "sigma");
    ang->SetBeamSigmaInAngX(sigma[0]);
    ang->SetBeamSigmaInAngY(sigma[1]);
  }

  // set the angle acceptance volume if needed
  auto d = py::dict(puser_info["direction"]);
  auto dd = py::dict(d["acceptance_angle"]);
  auto is_iso = ang->GetDistType() == "iso";
  auto &l = fThreadLocalDataAA.Get();
  l.fAAManager = new GateAcceptanceAngleTesterManager;
  l.fAAManager->Initialize(dd, is_iso);
  fSPS->SetAAManager(l.fAAManager);
}

void GateGenericSource::InitializeEnergy(py::dict puser_info) {
  /*
   * G4: Mono (mono-energetic), Lin (linear), Pow (power-law), Exp
   * (exponential), Gauss (gaussian), Brem (bremsstrahlung), BBody (black-body),
   * Cdg (cosmic diffuse gamma-ray), User (user-defined), Arb (arbitrary
   * point-wise), Epn (energy per nucleon).
   *
   * New interface: mono gauss // later 'user'
   *
   */
  auto user_info = py::dict(puser_info["energy"]);
  auto *ene = fSPS->GetEneDist();
  auto ene_type = DictGetStr(user_info, "type");
  auto is_cdf = DictGetBool(user_info, "is_cdf");

  // Get it
  if (ene_type == "mono") {
    ene->SetEnergyDisType("Mono");
    auto e = DictGetDouble(user_info, "mono");
    ene->SetMonoEnergy(e);
  }

  if (ene_type == "gauss") {
    ene->SetEnergyDisType("Gauss");
    auto e = DictGetDouble(user_info, "mono");
    ene->SetMonoEnergy(e);
    auto g = DictGetDouble(user_info, "sigma_gauss");
    ene->SetBeamSigmaInE(g);
  }

  if (ene_type == "range") {
    ene->SetEnergyDisType("range");
    auto emin = DictGetDouble(user_info, "min_energy");
    auto emax = DictGetDouble(user_info, "max_energy");
    ene->SetEmin(emin);
    ene->SetEmax(emax);
  }

  if (ene_type == "histogram") {
    ene->SetEnergyDisType("User");
    auto w = DictGetVecDouble(user_info, "histogram_weight");
    auto e = DictGetVecDouble(user_info, "histogram_energy");
    auto total = 0.0;
    for (unsigned long i = 0; i < w.size(); i++) {
      G4ThreeVector x(e[i], w[i], 0);
      ene->UserEnergyHisto(x);
      total += w[i];
    }
    // Modify the activity according to the total sum of weights
    fActivity = fActivity * total;
    fInitialActivity = fActivity;
  }

  if (ene_type == "spectrum_lines") {
    ene->SetEnergyDisType("spectrum_lines");
    auto w = DictGetVecDouble(user_info, "spectrum_weight");
    auto e = DictGetVecDouble(user_info, "spectrum_energy");
    auto total = 0.0;
    for (double i : w)
      total += i;
    for (unsigned long i = 0; i < w.size(); i++) {
      w[i] = w[i] / total;
    }
    for (unsigned long i = 1; i < w.size(); i++) {
      w[i] += w[i - 1];
    }
    ene->fEnergyCDF = e;
    ene->fProbabilityCDF = w;
    // Modify the activity according to the total sum of weights
    fActivity = fActivity * total;
    fInitialActivity = fActivity;
  }

  if (ene_type == "F18_analytic") {
    ene->SetEnergyDisType("F18_analytic");
  }

  if (ene_type == "O15_analytic") {
    ene->SetEnergyDisType("O15_analytic");
  }

  if (ene_type == "C11_analytic") {
    ene->SetEnergyDisType("C11_analytic");
  }

  if (is_cdf) {
    ene->SetEnergyDisType("CDF");
    ene->fEnergyCDF = fEnergyCDF;
    ene->fProbabilityCDF = fProbabilityCDF;
    // CDF should be set from py side
  }
}

void GateGenericSource::SetLifeTime(G4ParticleDefinition *p) {
  // Do nothing it the given life-time is negative (default)
  if (fUserParticleLifeTime < 0)
    return;
  // We set the LifeTime as proposed by the user
  p->SetPDGLifeTime(fUserParticleLifeTime);
}
