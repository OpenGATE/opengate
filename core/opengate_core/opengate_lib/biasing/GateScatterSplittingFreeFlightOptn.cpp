/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateScatterSplittingFreeFlightOptn.h"
#include "../GateHelpers.h"
#include "G4BiasingProcessInterface.hh"
#include "G4EmParameters.hh"
#include "G4GammaGeneralProcess.hh"
#include "G4ParticleChangeForGamma.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "GateScatterSplittingFreeFlightOptrActor.h"

GateScatterSplittingFreeFlightOptn::GateScatterSplittingFreeFlightOptn(
    const G4String &name, double *nbTracks)
    : G4VBiasingOperation(name), fSplittingFactor(1) {
  fAAManager = nullptr;
  fNbTracks = nbTracks;
  fUserTrackInformation = nullptr;
}

const G4VBiasingInteractionLaw *
GateScatterSplittingFreeFlightOptn::ProvideOccurenceBiasingInteractionLaw(
    const G4BiasingProcessInterface *, G4ForceCondition &) {
  return nullptr;
}

G4double GateScatterSplittingFreeFlightOptn::DistanceToApplyOperation(
    const G4Track *, G4double, G4ForceCondition *) {
  return DBL_MAX;
}

G4VParticleChange *
GateScatterSplittingFreeFlightOptn::GenerateBiasingFinalState(const G4Track *,
                                                              const G4Step *) {
  return nullptr;
}

void GateScatterSplittingFreeFlightOptn::SetSplittingFactor(
    const G4int splittingFactor) {
  fSplittingFactor = splittingFactor;
}

void GateScatterSplittingFreeFlightOptn::InitializeAAManager(
    const std::map<std::string, std::string> &user_info) {
  fAAManager = new GateAcceptanceAngleManager();
  fAAManager->Initialize(user_info, true);

  if (G4EmParameters::Instance()->GeneralProcessActive()) {
    Fatal("GeneralGammaProcess is not active. . This do *not* work for "
          "ScatterSplittingFreeFlight");
  }
}

G4VParticleChange *GateScatterSplittingFreeFlightOptn::ApplyFinalStateBiasing(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &b) {
  // This is the reference pure G4 version
  // return ApplyFinalStateBiasing_V1_PostStepDoIt(callingProcess, track, step,
  // b);

  // This is a faster (1x5 speedup) version with direct Compton sampling
  // return ApplyFinalStateBiasing_V3_SampleScatter(callingProcess, track, step,
  // b);
  return ApplyFinalStateBiasing_V4_SampleComptonOnly(callingProcess, track,
                                                     step, b);

  // Those are tests, not conclusive
  // return ApplyFinalStateBiasing_V2_SampleSecondaries(callingProcess, track,
  // step, b);
}

G4VParticleChange *
GateScatterSplittingFreeFlightOptn::ApplyFinalStateBiasing_V1_PostStepDoIt(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &) {

  // This is the initially scattered Gamma
  auto *final_state =
      callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
  auto particle_change = static_cast<G4ParticleChangeForGamma *>(final_state);

  const auto position = step->GetPostStepPoint()->GetPosition();
  fParticleChange.Initialize(*track);
  fParticleChange.ProposeTrackStatus(particle_change->GetTrackStatus());
  fParticleChange.ProposeEnergy(particle_change->GetProposedKineticEnergy());
  fParticleChange.ProposeMomentumDirection(
      particle_change->GetProposedMomentumDirection());

  // Copied from G4: "inform we take care of secondary weight (otherwise these
  // secondaries are by default given the primary weight)."
  fParticleChange.SetSecondaryWeightByProcess(true); // 'true' is needed

  // set the weight for the split track and the position
  const double weight = track->GetWeight() / fSplittingFactor;

  // delete secondaries to avoid memory leak (needed)
  for (auto j = 0; j < final_state->GetNumberOfSecondaries(); j++) {
    const auto *sec = final_state->GetSecondary(j);
    delete sec;
  }
  particle_change->Clear();

  G4Track templateTrack(*track);
  templateTrack.SetWeight(weight);
  templateTrack.SetPosition(position);

  // Loop to split Compton gammas (we cache the position, slightly faster)
  fAAManager->PrepareCheck(position);
  fAAManager->StartAcceptLoop();
  for (auto i = 0; i < fSplittingFactor; i++) {
    double energy = 0;
    final_state =
        callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
    particle_change = static_cast<G4ParticleChangeForGamma *>(final_state);

    // delete secondaries to avoid memory leak
    for (auto j = 0; j < final_state->GetNumberOfSecondaries(); j++) {
      const auto *sec = final_state->GetSecondary(j);
      delete sec;
    }

    // Angular Acceptance rejection, we ignore the secondary if not ok
    const auto momentum = particle_change->GetProposedMomentumDirection();
    if (!fAAManager->TestDirection(momentum)) {
      continue;
    }

    energy = particle_change->GetProposedKineticEnergy();
    if (energy > 0) {
      // Create a new track with another gamma (free by G4)
      const auto gammaTrack = new G4Track(templateTrack);
      gammaTrack->SetMomentumDirection(momentum);
      gammaTrack->SetKineticEnergy(energy);

      // indicate the track is an FF scatter split
      auto *track_info = new GateUserTrackInformation();
      track_info->SetGateTrackInformation(
          fActor,
          GateScatterSplittingFreeFlightOptrActor::fThisIsAFreeFlightTrack);
      gammaTrack->SetUserInformation(track_info);

      // Add the track in the stack
      fParticleChange.AddSecondary(gammaTrack);
    }

    particle_change->Clear(); // FIXME like in brem
  }

  // Count the nb of secondaries
  (*fNbTracks) += fParticleChange.GetNumberOfSecondaries();

  return &fParticleChange;
}

// --------------------------------------------------------------------
// ACCESSOR HACK: Expose the protected GetParticleChangeForGamma()
// --------------------------------------------------------------------
struct AccessorEmModel : public G4VEmModel {
  // Explicitly call the base constructor with a dummy name
  AccessorEmModel() : G4VEmModel("AccessorHack") {}

  // We expose the base class protected method as public here
  G4ParticleChangeForGamma *GetParticleChangeForGammaPublic() {
    return GetParticleChangeForGamma();
  }

  // Dummy implementations for pure virtuals (required to compile, but never
  // called)
  void Initialise(const G4ParticleDefinition *, const G4DataVector &) override {
  }
  void SampleSecondaries(std::vector<G4DynamicParticle *> *,
                         const G4MaterialCutsCouple *,
                         const G4DynamicParticle *, G4double,
                         G4double) override {}
};
// --------------------------------------------------------------------

G4VParticleChange *
GateScatterSplittingFreeFlightOptn::ApplyFinalStateBiasing_V2_SampleSecondaries(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &) {

  // ... (Keep your setup: fParticleChange initialization, weights,
  // templateTrack) ...
  fParticleChange.Initialize(*track);
  fParticleChange.SetSecondaryWeightByProcess(true); // vital

  // Update our Biasing ParticleChange with the Analog results
  auto *analog_state =
      callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
  auto *analog_change = static_cast<G4ParticleChangeForGamma *>(analog_state);
  fParticleChange.ProposeTrackStatus(analog_change->GetTrackStatus());
  fParticleChange.ProposeEnergy(analog_change->GetProposedKineticEnergy());
  fParticleChange.ProposeMomentumDirection(
      analog_change->GetProposedMomentumDirection());
  // Transfer the Analog Secondaries (e.g., Recoil Electron)
  for (auto j = 0; j < analog_state->GetNumberOfSecondaries(); j++) {
    fParticleChange.AddSecondary(analog_state->GetSecondary(j));
  }
  // Clear the temp object (but don't delete the secondaries, we moved them)
  analog_change->Clear();

  const double weight = track->GetWeight() / fSplittingFactor;
  const auto position = step->GetPostStepPoint()->GetPosition();

  G4Track templateTrack(*track);
  templateTrack.SetWeight(weight);
  templateTrack.SetPosition(position);

  // 1. Get the Physics Model
  const G4VEmProcess *emProcess = dynamic_cast<G4VEmProcess *>(
      const_cast<G4VProcess *>(callingProcess->GetWrappedProcess()));

  if (!emProcess)
    return nullptr;

  const auto *couple = track->GetMaterialCutsCouple();
  const double energy = track->GetKineticEnergy();
  G4VEmModel *currentModel =
      emProcess->SelectModelForMaterial(energy, couple->GetIndex());
  if (!currentModel)
    return nullptr; // Add this check!

  // 2. CAST TO ACCESSOR
  // This is safe because AccessorEmModel has the same memory layout as
  // G4VEmModel regarding the underlying 'pParticleChangeForGamma' pointer.
  auto *modelAccessor = reinterpret_cast<AccessorEmModel *>(currentModel);
  // auto* modelAccessor = static_cast<AccessorEmModel*>(currentModel);

  // 3. Prepare Geometry
  fAAManager->PrepareCheck(position);
  fAAManager->StartAcceptLoop();

  std::vector<G4DynamicParticle *> secondaries;

  // --- THE LOOP ---
  const double safeHighCut = 2.0 * track->GetKineticEnergy();
  // DDD(fSplittingFactor);
  for (auto i = 0; i < fSplittingFactor; i++) {

    // --- CRITICAL FIX: RESET MODEL STATE ---
    // We must tell the model's internal change object to reset to the track's
    // original state. Without this, iteration #2 sees the energy/status from
    // iteration #1.
    auto *modelPC = modelAccessor->GetParticleChangeForGammaPublic();
    modelPC->InitializeForPostStep(*track);

    // A. Sample with INFINITE CUT (DBL_MAX)
    // This updates the internal ParticleChange but prevents 'new
    // G4DynamicParticle'
    secondaries.clear();
    currentModel->SampleSecondaries(
        &secondaries, couple, track->GetDynamicParticle(),
        DBL_MAX,  // safeHighCut,
        DBL_MAX); // step->GetPostStepPoint()->GetSafety());

    // B. Access the result using the Accessor
    G4ThreeVector newMom = modelPC->GetProposedMomentumDirection();
    const double newEnergy = modelPC->GetProposedKineticEnergy();

    // C. Cleanup, for an unknown reason, still some secondaries sometimes
    for (const auto *sec : secondaries)
      delete sec;

    // D. Angular Acceptance
    if (!fAAManager->TestDirection(newMom)) {
      continue;
    }

    // E. Create Track
    if (newEnergy > 0) {
      const auto gammaTrack = new G4Track(templateTrack);
      gammaTrack->SetMomentumDirection(newMom);
      gammaTrack->SetKineticEnergy(newEnergy);

      // Attach User Info
      auto *track_info = new GateUserTrackInformation();
      track_info->SetGateTrackInformation(
          fActor,
          GateScatterSplittingFreeFlightOptrActor::fThisIsAFreeFlightTrack);
      gammaTrack->SetUserInformation(track_info);

      fParticleChange.AddSecondary(gammaTrack);
    }
  }

  (*fNbTracks) += fParticleChange.GetNumberOfSecondaries();
  return &fParticleChange;
}

double GateScatterSplittingFreeFlightOptn::SampleCompton_Butcher_method(
    double incidentEnergy, G4ThreeVector &direction) {

  // 1. Setup Constants (identical to G4KleinNishinaCompton.cc)
  const double electron_mass_c2 = CLHEP::electron_mass_c2;

  // Safety check for very low energy (though standard cuts usually catch this
  // earlier)
  if (incidentEnergy <= 100 * CLHEP::eV)
    return incidentEnergy;

  double E0_m = incidentEnergy / electron_mass_c2;

  double eps0 = 1. / (1. + 2. * E0_m);
  double epsilon0sq = eps0 * eps0;
  double alpha1 = -std::log(eps0);
  double alpha2 = alpha1 + 0.5 * (1. - epsilon0sq);

  double epsilon, epsilonsq, onecost, sint2, greject;

  // 2. Rejection Loop (Butcher & Messel)
  // "The random number techniques of Butcher & Messel are used (Nuc Phys
  // 20(1960),15)."
  do {
    // We need 3 random numbers (G4 uses flatArray, we use G4UniformRand for
    // simplicity)
    double r1 = G4UniformRand();
    double r2 = G4UniformRand();
    double r3 = G4UniformRand();

    if (alpha1 > alpha2 * r1) {
      // Branch A: 1/E distribution
      epsilon = std::exp(-alpha1 * r2);
      epsilonsq = epsilon * epsilon;
    } else {
      // Branch B: uniform epsilon^2
      epsilonsq = epsilon0sq + (1. - epsilon0sq) * r2;
      epsilon = std::sqrt(epsilonsq);
    }

    onecost = (1. - epsilon) / (epsilon * E0_m);
    sint2 = onecost * (2. - onecost);
    greject = 1. - epsilon * sint2 / (1. + epsilonsq);

    // G4 Loop condition: "while (greject < rndm[2])"
    // We break if the acceptance condition is met:
    if (greject >= r3)
      break;

  } while (true);

  // 3. Angular Rotation
  if (sint2 < 0.0)
    sint2 = 0.0;
  double cosTeta = 1. - onecost;
  double sinTeta = std::sqrt(sint2);
  double Phi = CLHEP::twopi * G4UniformRand();

  // Construct new direction in local frame
  G4ThreeVector newDir(sinTeta * std::cos(Phi), sinTeta * std::sin(Phi),
                       cosTeta);

  // Rotate to global frame defined by incident direction
  newDir.rotateUz(direction);

  direction = newDir;
  return epsilon * incidentEnergy;
}

double GateScatterSplittingFreeFlightOptn::SampleCompton_Khan_method(
    double incidentEnergy, G4ThreeVector &direction) {

  double E0_m = incidentEnergy / CLHEP::electron_mass_c2;
  double epsilon, oneMinusCosTheta, sinThetaSq, g;
  double rand1, rand2;

  // Kahn's rejection method (Standard G4 implementation)
  do {
    if (G4UniformRand() * (2 * E0_m + 1) < 1) {
      rand1 = G4UniformRand();
      rand2 = G4UniformRand();
      epsilon = 1. / (1. + 2 * E0_m * rand1);
      if (rand2 * rand2 > epsilon * epsilon)
        continue;
    } else {
      rand1 = G4UniformRand();
      rand2 = G4UniformRand();
      // CORRECTION: The epsilon calculation here was inverted in the previous
      // version This now matches G4KleinNishinaCompton.cc
      double x = (2 * E0_m + 1) / (1. + 2 * E0_m * rand1);
      epsilon = 1.0 / x;

      g = 1. - (1. - epsilon) / E0_m;
      if (rand2 > g)
        continue;
    }

    oneMinusCosTheta = (1. - epsilon) / E0_m;
    sinThetaSq = oneMinusCosTheta * (2. - oneMinusCosTheta);

    // Angular rejection loop
    if (G4UniformRand() >
        (1. - epsilon * sinThetaSq / (1. + epsilon * epsilon))) {
      continue;
    }
    break;
  } while (true);

  // Calculate new direction
  double cosTheta = 1. - oneMinusCosTheta;
  double sinTheta = std::sqrt(std::max(0., sinThetaSq));
  double phi = CLHEP::twopi * G4UniformRand();

  G4ThreeVector newDir(sinTheta * std::cos(phi), sinTheta * std::sin(phi),
                       cosTheta);
  newDir.rotateUz(
      direction); // Rotate reference frame to match incident momentum

  direction = newDir;
  return epsilon * incidentEnergy;
}

// -----------------------------------------------------------------------
// Manual Sampling: G4RayleighAngularGenerator (Standard Physics)
// Uses Dipole Approximation: (1 + cos^2(theta))
// -----------------------------------------------------------------------
double
GateScatterSplittingFreeFlightOptn::SampleRayleigh(double incidentEnergy,
                                                   G4ThreeVector &direction) {

  double cosTheta;
  // Sample cosTheta from (1 + cos^2(theta)) using rejection
  while (true) {
    cosTheta = 2.0 * G4UniformRand() - 1.0;
    if (G4UniformRand() <= 0.5 * (1.0 + cosTheta * cosTheta)) {
      break;
    }
  }

  double sinTheta = std::sqrt(std::max(0.0, 1.0 - cosTheta * cosTheta));
  double phi = CLHEP::twopi * G4UniformRand();

  G4ThreeVector newDir(sinTheta * std::cos(phi), sinTheta * std::sin(phi),
                       cosTheta);
  newDir.rotateUz(direction);

  direction = newDir;
  return incidentEnergy;
}

G4VParticleChange *
GateScatterSplittingFreeFlightOptn::ApplyFinalStateBiasing_V3_SampleScatter(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &) {

  // Init Particle Change
  fParticleChange.Initialize(*track);
  fParticleChange.SetSecondaryWeightByProcess(true);

  // Update our Biasing ParticleChange with the Analog results
  auto *analog_state =
      callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
  auto *analog_change = static_cast<G4ParticleChangeForGamma *>(analog_state);
  fParticleChange.ProposeTrackStatus(analog_change->GetTrackStatus());
  fParticleChange.ProposeEnergy(analog_change->GetProposedKineticEnergy());
  fParticleChange.ProposeMomentumDirection(
      analog_change->GetProposedMomentumDirection());
  // Transfer the Analog Secondaries (e.g., Recoil Electron)
  for (auto j = 0; j < analog_state->GetNumberOfSecondaries(); j++) {
    fParticleChange.AddSecondary(analog_state->GetSecondary(j));
  }
  // Clear the temp object (but don't delete the secondaries, we moved them)
  analog_change->Clear();

  const double weight = track->GetWeight() / fSplittingFactor;
  const auto position = step->GetPostStepPoint()->GetPosition();

  // Identify Process Type (13 = Compton, 11 = Rayleigh)
  // We trust the Actor has already validated this is a scattering process
  int processSubType = callingProcess->GetWrappedProcess()->GetProcessSubType();

  // Prepare Geometry Check
  fAAManager->PrepareCheck(position);
  fAAManager->StartAcceptLoop();

  G4Track templateTrack(*track);
  templateTrack.SetWeight(weight);
  templateTrack.SetPosition(position);

  // Pre-fetch initial kinematics
  const double initialEnergy = track->GetKineticEnergy();
  const G4ThreeVector initialDir = track->GetMomentumDirection();

  // --- FAST LOOP ---
  for (auto i = 0; i < fSplittingFactor; i++) {

    double newEnergy = 0;
    G4ThreeVector newMom = initialDir;

    // 1. Sample Math (No memory allocation!)
    if (processSubType == 13) {
      newEnergy = SampleCompton_Butcher_method(initialEnergy, newMom);
    } else if (processSubType == 11) {
      newEnergy = SampleRayleigh(initialEnergy, newMom);
    } else {
      // Should not happen if Actor filters correctly
      continue;
    }

    // 2. Angular Acceptance Check (Optimized)
    if (!fAAManager->TestDirection(newMom)) {
      continue;
    }

    // 3. Create Track
    if (newEnergy > 0) {
      const auto gammaTrack = new G4Track(templateTrack);
      gammaTrack->SetMomentumDirection(newMom);
      gammaTrack->SetKineticEnergy(newEnergy);

      auto *track_info = new GateUserTrackInformation();
      track_info->SetGateTrackInformation(
          fActor,
          GateScatterSplittingFreeFlightOptrActor::fThisIsAFreeFlightTrack);
      gammaTrack->SetUserInformation(track_info);

      fParticleChange.AddSecondary(gammaTrack);
    }
  }

  (*fNbTracks) += fParticleChange.GetNumberOfSecondaries();
  return &fParticleChange;
}

G4VParticleChange *
GateScatterSplittingFreeFlightOptn::ApplyFinalStateBiasing_V4_SampleComptonOnly(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &) {

  // 1. INITIALIZE
  const auto position = step->GetPostStepPoint()->GetPosition();
  fParticleChange.Initialize(*track);
  fParticleChange.SetSecondaryWeightByProcess(true);

  // 2. ANALOG PRIMARY (Run Standard G4 Physics)
  // This ensures the primary/recoil electron are handled exactly by Geant4
  auto *analog_state =
      callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
  auto *analog_change = static_cast<G4ParticleChangeForGamma *>(analog_state);

  fParticleChange.ProposeTrackStatus(analog_change->GetTrackStatus());
  fParticleChange.ProposeEnergy(analog_change->GetProposedKineticEnergy());
  fParticleChange.ProposeMomentumDirection(
      analog_change->GetProposedMomentumDirection());

  for (auto j = 0; j < analog_state->GetNumberOfSecondaries(); j++) {
    fParticleChange.AddSecondary(analog_state->GetSecondary(j));
  }
  analog_change->Clear();

  // 3. SPLITTING LOOP (The Hybrid Optimization)
  // -------------------------------------------
  int processSubType = callingProcess->GetWrappedProcess()->GetProcessSubType();

  // Prepare Geometry (Optimization)
  fAAManager->PrepareCheck(position);
  fAAManager->StartAcceptLoop();

  const double splitWeight = track->GetWeight() / fSplittingFactor;
  G4Track templateTrack(*track);
  templateTrack.SetWeight(splitWeight);
  templateTrack.SetPosition(position);

  const double initialEnergy = track->GetKineticEnergy();
  const G4ThreeVector initialDir = track->GetMomentumDirection();

  for (auto i = 0; i < fSplittingFactor; i++) {

    double newEnergy = 0;
    G4ThreeVector newMom = initialDir;
    bool isSplitGenerated = false;

    if (processSubType == 13) {
      // --- CASE A: COMPTON (Manual Sampling) ---
      // Fast & Accurate for standard physics
      newEnergy = SampleCompton_Butcher_method(initialEnergy, newMom);
      isSplitGenerated = true;

    } else if (processSubType == 11) {
      // --- CASE B: RAYLEIGH (Geant4 PostStepDoIt) ---
      // We Delegate to G4 because Manual Dipole is too broad.
      // This preserves Forward Peaking from Atomic Form Factors.
      auto *split_state = callingProcess->GetWrappedProcess()->PostStepDoIt(
          templateTrack, *step);
      auto *split_change = static_cast<G4ParticleChangeForGamma *>(split_state);

      newEnergy = split_change->GetProposedKineticEnergy();
      newMom = split_change->GetProposedMomentumDirection();

      // Clean up G4's temp secondaries (Rayleigh has none usually, but safe to
      // check)
      for (auto j = 0; j < split_state->GetNumberOfSecondaries(); j++)
        delete split_state->GetSecondary(j);
      split_change->Clear();

      isSplitGenerated = true;
    }

    if (!isSplitGenerated)
      continue;

    // Angular Acceptance Check (Optimized)
    if (!fAAManager->TestDirection(newMom)) {
      continue;
    }

    // Create Track
    if (newEnergy > 0) {
      const auto gammaTrack = new G4Track(templateTrack);
      gammaTrack->SetMomentumDirection(newMom);
      gammaTrack->SetKineticEnergy(newEnergy);

      auto *track_info = new GateUserTrackInformation();
      track_info->SetGateTrackInformation(
          fActor,
          GateScatterSplittingFreeFlightOptrActor::fThisIsAFreeFlightTrack);
      gammaTrack->SetUserInformation(track_info);

      fParticleChange.AddSecondary(gammaTrack);
    }
  }

  (*fNbTracks) += fParticleChange.GetNumberOfSecondaries();
  return &fParticleChange;
}