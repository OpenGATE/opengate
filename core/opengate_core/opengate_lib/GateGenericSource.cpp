/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGenericSource.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include <G4CallbackModel.hh>
#include <G4IonTable.hh>
#include <G4ParticleTable.hh>
#include <G4RandomTools.hh>
#include <G4UImanager.hh>
#include <G4UnitsTable.hh>
#include <G4VisManager.hh>
#include <algorithm>
#include <fmt/core.h>
#include <iterator>
#include <numeric>
#include <pybind11/pytypes.h>

GateGenericSource::GateGenericSource() : GateVSource() {
  fA = 0;
  fZ = 0;
  fE = 0;
  fWeight = -1;
  fWeightSigma = -1;
  fInitialActivity = 0;
  fParticleDefinition = nullptr;
  fDirectionRelativeToAttachedVolume = false;
  fUserParticleLifeTime = -1;
  fBackToBackMode = false;
  fSPS = nullptr;
  fAAManager = nullptr;
  fFDManager = nullptr;
  fInitConfine = false;
  fInitGenericIon = false;
  fEffectiveEventTime = -1;
  fCurrentSkippedEvents = 0;
  fCurrentZeroEvents = 0;
}

GateGenericSource::~GateGenericSource() {
  // FIXME: we cannot really delete fSPS and fAAManager
  // I dont know exactly why.
  // Maybe because it has been created in a thread which
  // can be different from the thread that delete.
  if (fAAManager != nullptr) {
    // delete fAAManager;
  }
  // delete fSPS;
}

void GateGenericSource::CleanWorkerThread() {
  // Not used yet. Maybe later to clean local data in a thread.
}

void GateGenericSource::CreateSPS() {
  fSPS = new GateSingleParticleSource(fAttachedToVolumeName);
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

  // weight
  fWeight = DictGetDouble(user_info, "weight");
  fWeightSigma = DictGetDouble(user_info, "weight_sigma");
  fUserParticleLifeTime = DictGetDouble(user_info, "user_particle_life_time");

  // get the user info for the particle
  InitializeParticle(user_info);

  // position, direction, energy
  InitializePosition(user_info);
  InitializeDirection(user_info);
  InitializeEnergy(user_info);
  InitializePolarization(user_info);
  InitializeVisualization(user_info);

  // init number of events
  fDirectionRelativeToAttachedVolume =
      DictGetBool(user_info, "direction_relative_to_attached_volume");
}

void GateGenericSource::UpdateActivity(const double time) {
  if (!fTAC_Times.empty())
    return UpdateActivityWithTAC(time);
  GateVSource::UpdateActivity(time);
}

void GateGenericSource::UpdateActivityWithTAC(const double time) {
  // Below/above the TAC ?
  if (time < fTAC_Times.front() || time > fTAC_Times.back()) {
    fActivity = 0;
    return;
  }

  // Search for the time bin
  const auto lower =
      std::lower_bound(fTAC_Times.begin(), fTAC_Times.end(), time);
  auto i = std::distance(fTAC_Times.begin(), lower);

  // Exact match or first sample
  if (i == 0) {
    fActivity = fTAC_Activities[0];
    return;
  }

  // Move to the lower bin edge for the interpolation
  i -= 1;

  // Last element ?
  if (i >= fTAC_Times.size() - 1) {
    fActivity = fTAC_Activities.back();
    return;
  }

  // linear interpolation
  const double bin_time = fTAC_Times[i + 1] - fTAC_Times[i];
  const double w1 = (fTAC_Times[i + 1] - time) / bin_time;
  const double w2 = (time - fTAC_Times[i]) / bin_time;
  fActivity = fTAC_Activities[i] * w1 + fTAC_Activities[i + 1] * w2;
}

double
GateGenericSource::PrepareNextTime(const double current_simulation_time,
                                   unsigned long NumberOfGeneratedEvents) {
  // initialization of the effective event time (it can be in the
  // future according to the current_simulation_time)
  if (fEffectiveEventTime < current_simulation_time) {
    fEffectiveEventTime = current_simulation_time;
  }
  fTotalSkippedEvents += fCurrentSkippedEvents;
  fTotalZeroEvents += fCurrentZeroEvents;
  fCurrentZeroEvents = 0;
  const auto cse = fCurrentSkippedEvents;
  fCurrentSkippedEvents = 0;

  return GateVSource::PrepareNextTime(fEffectiveEventTime,
                                      NumberOfGeneratedEvents + cse);
}

void GateGenericSource::PrepareNextRun() {
  // The following function computes the global transformation from
  // the local volume (mother) to the world
  GateVSource::PrepareNextRun();

  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
  auto *pos = fSPS->GetPosDist();
  pos->SetCentreCoords(fGlobalTranslation);

  // orientation according to mother volume
  const auto rotation = fGlobalRotation;
  const G4ThreeVector r1(rotation(0, 0), rotation(1, 0), rotation(2, 0));
  const G4ThreeVector r2(rotation(0, 1), rotation(1, 1), rotation(2, 1));
  pos->SetPosRot1(r1);
  pos->SetPosRot2(r2);

  // For the direction, the orientation may or may not be
  // relative to the volume according to the user option
  auto *ang = fSPS->GetAngDist();
  ang->fDirectionRelativeToAttachedVolume = fDirectionRelativeToAttachedVolume;
  ang->fGlobalRotation = fGlobalRotation;
  ang->fGlobalTranslation = fGlobalTranslation;
  if (fangType == "momentum" && fDirectionRelativeToAttachedVolume) {
    const auto new_d = rotation * fInitializeMomentum;
    ang->SetParticleMomentumDirection(new_d);
    ang->fDirectionRelativeToAttachedVolume = false;
  }
  if (fangType == "focused" && fDirectionRelativeToAttachedVolume) {
    const auto vec_f = fInitializeFocusPoint - fInitTranslation;
    const auto rot_f = rotation * vec_f;
    const auto new_f = rot_f + fGlobalTranslation;
    ang->SetFocusPoint(new_f);
    ang->fDirectionRelativeToAttachedVolume = false;
  }
}

void GateGenericSource::UpdateEffectiveEventTime(
    const double current_simulation_time,
    const unsigned long skipped_particle) {
  unsigned long n = 0;
  fEffectiveEventTime = current_simulation_time;
  while (n < skipped_particle && fEffectiveEventTime < fEndTime) {
    fEffectiveEventTime =
        fEffectiveEventTime - log(G4UniformRand()) * (1.0 / fActivity);
    n++;
  }
}

void GateGenericSource::GeneratePrimaries(
    G4Event *event, const double current_simulation_time) {
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
  // (the acceptance angle or forced direction is included)
  fSPS->SetParticleTime(current_simulation_time);
  fSPS->GeneratePrimaryVertex(event);

  // update the time according to skipped events
  fEffectiveEventTime = current_simulation_time;
  if (fAAManager->IsEnabled()) {
    if (fAAManager->GetPolicy() == GateAcceptanceAngleManager::AASkipEvent) {
      UpdateEffectiveEventTime(current_simulation_time,
                               fAAManager->GetNumberOfNotAcceptedEvents());
      fCurrentSkippedEvents = fAAManager->GetNumberOfNotAcceptedEvents();
      event->GetPrimaryVertex(0)->SetT0(fEffectiveEventTime);
    } else {
      fCurrentZeroEvents = fAAManager->GetNumberOfNotAcceptedEvents(); // 1 or 0
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

  fRunGeneratedEvents++;
}

void GateGenericSource::InitializeParticle(py::dict &user_info) {
  std::string pname = DictGetStr(user_info, "particle");
  // Is the particle an ion (name start with ion) ?
  if (pname.rfind("ion", 0) == 0) {
    InitializeIon(user_info);
    return;
  }
  fInitGenericIon = false;
  // Is the particle a back to back ?
  if (pname.rfind("back_to_back") == 0) {
    InitializeBackToBackMode(user_info);
    return;
  }
  fBackToBackMode = false;
  // other conventional particle type
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

void GateGenericSource::InitializeBackToBackMode(py::dict &user_info) {
  auto u = py::dict(user_info["direction"]);
  bool accolinearityFlag = DictGetBool(u, "accolinearity_flag");
  fSPS->SetBackToBackMode(true, accolinearityFlag);
  if (accolinearityFlag == true) {
    // Change the value if user provided one.
    double accolinearityFWHM = DictGetDouble(u, "accolinearity_fwhm");
    fSPS->SetAccolinearityFWHM(accolinearityFWHM);
  }
  // this is photon
  auto *particle_table = G4ParticleTable::GetParticleTable();
  fParticleDefinition = particle_table->FindParticle("gamma");
  fSPS->SetParticleDefinition(fParticleDefinition);
  // The energy is fixed to 511 keV in the python side
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
  std::vector<std::string> l = {"sphere", "point",    "box",
                                "disc",   "cylinder", "surface_sphere"};
  CheckIsIn(pos_type, l);
  auto translation = DictGetG4ThreeVector(user_info, "translation");
  fInitTranslation = translation;
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
  if (pos_type == "surface_sphere") {
    pos->SetPosDisType("Surface");
    pos->SetPosDisShape("Sphere");
  }

  // radius for sphere, disc, cylinder, surface_sphere
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
  // SetOrientationAccordingToAttachedVolume)
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
  fangType = ang_type;
  std::vector<std::string> llt = {"iso",     "histogram", "momentum",
                                  "focused", "beam2d",    "cos"};
  CheckIsIn(ang_type, llt);

  if (ang_type == "iso" || ang_type == "cos") {
    ang->SetAngDistType(ang_type);

    auto theta = DictGetVecDouble(user_info, "theta");
    ang->SetMinTheta(theta[0]);
    ang->SetMaxTheta(theta[1]);

    auto phi = DictGetVecDouble(user_info, "phi");
    ang->SetMinPhi(phi[0]);
    ang->SetMaxPhi(phi[1]);
  }

  if (ang_type == "momentum") {
    ang->SetAngDistType("planar"); // FIXME really ??
    auto d = DictGetG4ThreeVector(user_info, "momentum");
    fInitializeMomentum = d;
    ang->SetParticleMomentumDirection(d);
  }

  if (ang_type == "focused") {
    ang->SetAngDistType("focused");
    auto f = DictGetG4ThreeVector(user_info, "focus_point");
    fInitializeFocusPoint = f;
    ang->SetFocusPoint(f);
  }

  if (ang_type == "beam2d") {
    ang->SetAngDistType("beam2d");
    auto sigma = DictGetVecDouble(user_info, "sigma");
    ang->SetBeamSigmaInAngX(sigma[0]);
    ang->SetBeamSigmaInAngY(sigma[1]);
  }

  if (ang_type == "histogram") {
    ang->SetAngDistType("user");

    auto theta_w = DictGetVecDouble(user_info, "histogram_theta_weights");
    auto theta_e = DictGetVecDouble(user_info, "histogram_theta_angles");

    if (theta_w.size() + 1 != theta_e.size())
      Fatal("GenericSource angular distribution type 'histogram' requires "
            "'histogram_theta_weights' to have exactly one element less than "
            "'histogram_theta_angles'.");

    /* TODO
     * better general solution would be to add a setter_hook Python-side
     * on the histogram_theta/phi_weight to prepend a 0
     */
    ang->UserDefAngTheta({theta_e[0], 0, 0});
    for (std::size_t i = 1; i < theta_e.size(); i++)
      ang->UserDefAngTheta({theta_e[i], theta_w[i - 1], 0});

    auto phi_w = DictGetVecDouble(user_info, "histogram_phi_weights");
    auto phi_e = DictGetVecDouble(user_info, "histogram_phi_angles");

    if (phi_w.size() + 1 != phi_e.size())
      Fatal("GenericSource angular distribution type 'histogram' requires "
            "'histogram_phi_weights' to have exactly one element less than "
            "'histogram_phi_angles'.");

    ang->UserDefAngPhi({phi_e[0], 0, 0});
    for (std::size_t i = 1; i < phi_e.size(); i++)
      ang->UserDefAngPhi({phi_e[i], phi_w[i - 1], 0});
  }

  // set the angle acceptance volume if needed
  const auto d = py::dict(puser_info["direction"]);
  auto dd = DictToMap(d["angular_acceptance"]);
  const auto is_valid_type =
      ang->GetDistType() == "iso" || ang->GetDistType() == "user";
  fAAManager = new GateAcceptanceAngleManager;
  fAAManager->Initialize(dd, is_valid_type);
  fSPS->SetAAManager(fAAManager);

  // set Forced Direction
  fFDManager = new GateForcedDirectionManager;
  fFDManager->Initialize(dd, ang->GetDistType() == "iso");
  fSPS->SetFDManager(fFDManager);
}

void GateGenericSource::InitializePolarization(py::dict puser_info) {
  // Set the polarization
  auto polarization = DictGetVecDouble(puser_info, "polarization");
  if (polarization.size() == 3) {
    auto polarisation_tree_vector =
        G4ThreeVector(polarization[0], polarization[1], polarization[2]);
    fSPS->SetPolarization(polarisation_tree_vector);
  }
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

  if (ene_type == "spectrum_discrete") { // TODO rename
    auto weights = DictGetVecDouble(user_info, "spectrum_weights");
    auto energies = DictGetVecDouble(user_info, "spectrum_energies");

    if (weights.empty())
      Fatal("The weights for " + fName + " is zero length. Abort");
    if (energies.empty())
      Fatal("The energies for " + fName + " is zero length. Abort");
    if (weights.size() != energies.size()) {
      auto const errorMessage =
          fmt::format("For {}, the spectrum vectors weights and energies"
                      " must have the same size ({} ≠ {})",
                      fName, weights.size(), energies.size());
      Fatal(errorMessage);
    }

    // cumulated weights
    std::partial_sum(std::begin(weights), std::end(weights),
                     std::begin(weights));
    auto const weightsSum = weights.back();

    // normalize weights to total
    for (auto &weight : weights)
      weight /= weightsSum;

    // ! important !
    // Modify the activity according to the total sum of weights because we
    // normalize the weights
    fActivity *= weightsSum;
    fInitialActivity = fActivity;

    ene->SetEnergyDisType(ene_type);
    ene->SetEmin(energies.front());
    ene->SetEmax(energies.back());
    ene->fEnergyCDF = energies;
    ene->fProbabilityCDF = weights;
  }

  if (ene_type == "spectrum_histogram") {
    auto weights = DictGetVecDouble(user_info, "spectrum_weights");
    auto energy_bin_edges =
        DictGetVecDouble(user_info, "spectrum_energy_bin_edges");
    auto interpolation =
        DictGetStr(user_info, "spectrum_histogram_interpolation");

    if (weights.empty())
      Fatal("The weights for " + fName + " is zero length. Abort");
    if (energy_bin_edges.empty())
      Fatal("The energy_bin_edges for " + fName + " is zero length. Abort");
    if ((weights.size() + 1) != energy_bin_edges.size()) {
      auto const errorMessage = fmt::format(
          "For {}, the spectrum vector energy_bin_edges must have exactly one"
          " more element than the vector weights ({} ≠ {} + 1)",
          fName, energy_bin_edges.size(), weights.size());
      Fatal(errorMessage);
    }

    if (interpolation == "None" || interpolation == "none") {
      double accumulatedWeights = 0;
      for (std::size_t i = 0; i < weights.size(); ++i) {
        auto const diffEnergy = energy_bin_edges[i + 1] - energy_bin_edges[i];
        accumulatedWeights += weights[i] * diffEnergy;
        weights[i] = accumulatedWeights;
      }
    } else if (interpolation == "linear") {
      double accumulatedWeights = 0;
      for (std::size_t i = 0; i < weights.size(); i++) {
        auto const diffEnergy = energy_bin_edges[i + 1] - energy_bin_edges[i];
        auto const diffWeight = weights[i + 1] - weights[i];
        accumulatedWeights +=
            diffEnergy * weights[i] - 0.5 * diffEnergy * diffWeight;
        weights[i] = accumulatedWeights;
      }
    } else
      Fatal("For " + fName +
            ", invalid spectrum interpolation type: " + interpolation);

    auto const weightsSum = weights.back();

    // normalize weights to total
    for (auto &weight : weights)
      weight /= weightsSum;

    // ! important !
    // Modify the activity according to the total sum of weights because we
    // normalize the weights
    fActivity *= weightsSum;
    fInitialActivity = fActivity;

    std::string interpolation_str;
    if (interpolation != "None" && interpolation != "none")
      interpolation_str =
          (interpolation != "none" ? ("_" + interpolation) : "");

    ene->SetEnergyDisType(ene_type + interpolation_str);
    ene->SetEmin(energy_bin_edges.front());
    ene->SetEmax(energy_bin_edges.back());
    ene->fEnergyCDF = energy_bin_edges;
    ene->fProbabilityCDF = weights;
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
  // Do nothing if the given life-time is negative (default)
  if (fUserParticleLifeTime < 0)
    return;
  // We set the LifeTime as proposed by the user
  p->SetPDGLifeTime(fUserParticleLifeTime);
}

unsigned long GateGenericSource::GetTotalSkippedEvents() const {
  return fTotalSkippedEvents;
}

unsigned long GateGenericSource::GetTotalZeroEvents() const {
  return fTotalZeroEvents;
}

void GateGenericSource::InitializeVisualization(py::dict puser_info) {
  if (G4Threading::IsWorkerThread())
    return;
  auto user_info = py::dict(puser_info["visualization"]);
  py::object color = user_info["color"];
  if (py::isinstance<py::str>(color)) {
    std::string color_str = color.cast<std::string>();
    G4Colour::GetColour(color_str, fVisColour);
  } else {
    std::vector<G4double> rgba = color.cast<std::vector<G4double>>();
    fVisColour = G4Colour(rgba[0], rgba[1], rgba[2], rgba[3]);
  }

  fVisSize = DictGetDouble(user_info, "size");
  fVisCount = DictGetInt(user_info, "count");
}

GateGenericSource::PosPointCloud::PosPointCloud(const G4Colour &colour,
                                                G4double size) {
  fPolymarker.SetMarkerType(G4Polymarker::circles);
  fPolymarker.SetSize(G4VMarker::screen, size);
  fPolymarker.SetFillStyle(G4VMarker::filled);
  fPolymarker.SetVisAttributes(G4VisAttributes(colour));
}

void GateGenericSource::PosPointCloud::operator()(
    G4VGraphicsScene &sceneHandler, const G4ModelingParameters *) {
  sceneHandler.BeginPrimitives();
  sceneHandler.AddPrimitive(fPolymarker);
  sceneHandler.EndPrimitives();
}

void GateGenericSource::Visualize() const {
  if (fVisCount <= 0)
    return;

  G4VisManager *vis_manager = G4VisManager::GetInstance();
  auto *scene = vis_manager->GetCurrentScene();

  auto *pos = fSPS->GetPosDist();

  auto *point_cloud = new PosPointCloud(fVisColour, fVisSize);
  for (int k = 0; k < fVisCount; ++k) {
    G4ThreeVector position = pos->VGenerateOne();
    point_cloud->fPolymarker.push_back(position);
  }

  auto *model = new G4CallbackModel<PosPointCloud>(point_cloud);
  model->SetType("Generic source point cloud");
  model->SetGlobalTag("Generic source point cloud");
  std::ostringstream description;
  description << "Generic source point cloud: " << fName << " (" << fVisCount
              << " points) " << point_cloud;
  model->SetGlobalDescription(description.str());

  const auto successful = scene->AddRunDurationModel(model, true);
  if (!successful) {
    G4Exception("GateGenericSource::Visualize", "VisualizationError",
                JustWarning,
                "Failed to add the visualization model to the scene.");
  }

  auto *ui = G4UImanager::GetUIpointer();
  ui->ApplyCommand("/vis/scene/notifyHandlers");
  ui->ApplyCommand("/vis/viewer/update");
}
