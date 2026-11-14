//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
//
/// \file GateLastVertexInteractionSplittingActor.cc
/// \brief Implementation of the GateLastVertexInteractionSplittingActor class

#include "GateLastVertexInteractionSplittingActor.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateLastVertexSource.h"
#include "GateLastVertexSplittingPostStepDoIt.h"
#include "GateSourceManager.h"
#include <G4ParticleTable.hh>
#include <G4ProcessManager.hh>
#include <G4ProcessVector.hh>
#include <G4RunManager.hh>
#include <G4TrackStatus.hh>
#include <G4VParticleChange.hh>
#include <G4eplusAnnihilation.hh>
#include <cmath>

G4Mutex SetEventCorrectionForLastVertex = G4MUTEX_INITIALIZER;

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateLastVertexInteractionSplittingActor::
    GateLastVertexInteractionSplittingActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("EndOfSimulationWorkerAction");
}

void GateLastVertexInteractionSplittingActor::InitializeUserInfo(
    py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fAttachedToVolumeName = DictGetStr(user_info, "attached_to");
  fSplittingFactor = DictGetDouble(user_info, "splitting_factor");
  fBatchSize = DictGetDouble(user_info, "batch_size");
  fNbOfMaxBatchPerEvent = DictGetInt(user_info, "nb_of_max_batch_per_event");
  auto dd = DictToMap(user_info["angular_acceptance"]);
  this->InitializeAAManager(dd);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void GateLastVertexInteractionSplittingActor::InitializeAAManager(
    const std::map<std::string, std::string> &user_info) {
  fAcceptanceAngleParameters = user_info;
  GateAcceptanceAngleManager validation;
  validation.Initialize(user_info, true);

  if (G4EmParameters::Instance()->GeneralProcessActive() == true) {
    Fatal("GeneralGammaProcess is not active. . This do *not* work for "
          "ScatterSplittingFreeFlight");
  }
}

G4VProcess *GateLastVertexInteractionSplittingActor::GetProcessFromProcessName(
    G4String particleName, G4String pName) {
  auto *particle_table = G4ParticleTable::GetParticleTable();
  G4ParticleDefinition *particleDefinition =
      particle_table->FindParticle(particleName);
  if (!particleDefinition)
    Fatal("LastVertex: particle '" + particleName +
          "' not found while looking up process '" + pName + "'");
  G4ProcessManager *processManager = particleDefinition->GetProcessManager();
  if (!processManager)
    Fatal("LastVertex: no process manager for particle '" + particleName +
          "' while looking up process '" + pName + "'");
  G4ProcessVector *processList = processManager->GetProcessList();
  for (size_t i = 0; i < processList->size(); ++i) {
    auto process = (*processList)[i];
    if (process->GetProcessName() == pName) {
      return process;
    }
  }
  Fatal("LastVertex: process '" + pName + "' not found for particle '" +
        particleName + "'; cannot split this interaction");
  return nullptr; // Fatal throws; no splitting is attempted.
}

G4Track *GateLastVertexInteractionSplittingActor::CreateATrackFromContainer(
    LastVertexDataContainer theContainer) {

  auto *particle_table = G4ParticleTable::GetParticleTable();
  SimpleContainer container = theContainer.GetContainerToSplit();
  if (container.GetParticleNameToSplit() != "None") {
    G4ParticleDefinition *particleDefinition =
        particle_table->FindParticle(container.GetParticleNameToSplit());
    G4ThreeVector momentum = container.GetMomentum();
    G4double energy = container.GetEnergy();
    if (energy < 0) {
      energy = 0;
      momentum = {0, 0, 0};
    }
    G4int trackStatus = container.GetTrackStatus();
    G4ThreeVector position = container.GetVertexPosition();
    G4ThreeVector polarization = container.GetPolarization();
    G4DynamicParticle *dynamicParticle =
        new G4DynamicParticle(particleDefinition, momentum, energy);
    G4double time = 0;
    G4Track *aTrack = new G4Track(dynamicParticle, time, position);
    aTrack->SetTouchableHandle(container.GetTouchableHandle());
    aTrack->SetPolarization(polarization);
    if (trackStatus == 0) {
      aTrack->SetTrackStatus(fAlive);
    }
    if (trackStatus == 1) {
      aTrack->SetTrackStatus(fStopButAlive);
    }
    if ((trackStatus == 2) || (trackStatus == 3)) {
      aTrack->SetTrackStatus(fAlive);
    }
    aTrack->SetWeight(container.GetWeight());
    return aTrack;
  }

  return nullptr;
}

G4Track *GateLastVertexInteractionSplittingActor::CreateComptonTrack(
    G4ParticleChangeForGamma *gammaProcess, G4Track track, G4double weight) {

  G4double energy = gammaProcess->GetProposedKineticEnergy();
  G4ThreeVector polarization = gammaProcess->GetProposedPolarization();
  const G4ThreeVector momentum = gammaProcess->GetProposedMomentumDirection();
  const G4ThreeVector position = track.GetPosition();
  G4Track *newTrack = new G4Track(track);

  newTrack->SetKineticEnergy(energy);
  newTrack->SetMomentumDirection(momentum);
  newTrack->SetPosition(position);
  newTrack->SetPolarization(polarization);
  newTrack->SetWeight(weight);
  return newTrack;
}

void GateLastVertexInteractionSplittingActor::ComptonSplitting(
    G4Step *initStep, G4VProcess *process, G4double batchSize) {
  auto &data = fWorkerState.Get();

  GateGammaEmPostStepDoIt *emProcess = (GateGammaEmPostStepDoIt *)process;
  for (int i = 0; i < batchSize; i++) {
    G4VParticleChange *processFinalState =
        emProcess->PostStepDoIt(*data.fTrackToSplit, *initStep);
    G4ParticleChangeForGamma *gammaProcessFinalState =
        (G4ParticleChangeForGamma *)processFinalState;

    G4Track *newTrack = CreateComptonTrack(gammaProcessFinalState,
                                           *data.fTrackToSplit, data.fWeight);

    if ((data.fAAManager != 0) &&
        (!(data.fAAManager->TestIfAccept(newTrack->GetPosition(),
                                         newTrack->GetMomentumDirection())))) {
      delete newTrack;
    } else {
      data.fStackManager->PushOneTrack(newTrack);
    }

    // Special case here, since we generate independently each particle, we will
    // not attach an electron to exiting compton photon, but we will the
    // secondaries.

    if (processFinalState->GetNumberOfSecondaries() > 0) {
      delete processFinalState->GetSecondary(0);
    }

    processFinalState->Clear();
    gammaProcessFinalState->Clear();
  }
}

G4Track
GateLastVertexInteractionSplittingActor::eBremProcessFinalState(G4Track *track,
                                                                G4Step *step) {
  // It seem's that the the along step method apply only to brem results to no
  // deposited energy but a change in momentum direction according to the
  // process Whereas the along step method applied to the ionisation well change
  // the deposited energy but not the momentum. Then I apply both to have a
  // correct momentum and deposited energy before the brem effect.
  G4String particleName = track->GetDefinition()->GetParticleName();
  G4VProcess *eIoniProcess = GetProcessFromProcessName(particleName, "eIoni");
  G4VProcess *eBremProcess = GetProcessFromProcessName(particleName, "eBrem");
  G4VParticleChange *eIoniProcessAlongState =
      eIoniProcess->AlongStepDoIt(*track, *step);
  G4VParticleChange *eBremProcessAlongState =
      eBremProcess->AlongStepDoIt(*track, *step);
  G4ParticleChangeForLoss *eIoniProcessAlongStateForLoss =
      (G4ParticleChangeForLoss *)eIoniProcessAlongState;
  G4ParticleChangeForLoss *eBremProcessAlongStateForLoss =
      (G4ParticleChangeForLoss *)eBremProcessAlongState;
  G4double LossEnergy = eIoniProcessAlongStateForLoss->GetLocalEnergyDeposit();
  G4ThreeVector momentum =
      eBremProcessAlongStateForLoss->GetProposedMomentumDirection();
  G4ThreeVector polarization =
      eBremProcessAlongStateForLoss->GetProposedPolarization();
  G4Track aTrack = G4Track(*track);

  aTrack.SetKineticEnergy(track->GetKineticEnergy() - LossEnergy);
  aTrack.SetMomentumDirection(momentum);
  aTrack.SetPolarization(polarization);
  eIoniProcessAlongState->Clear();
  eBremProcessAlongState->Clear();
  return aTrack;
}

void GateLastVertexInteractionSplittingActor::SecondariesSplitting(
    G4Step *initStep, G4VProcess *process, LastVertexDataContainer theContainer,
    G4double batchSize) {
  auto &data = fWorkerState.Get();
  SimpleContainer container = theContainer.GetContainerToSplit();

  G4VParticleChange *processFinalState = nullptr;
  GateBremPostStepDoIt *bremProcess = nullptr;
  GateGammaEmPostStepDoIt *emProcess = nullptr;
  GateplusannihilAtRestDoIt *eplusAnnihilProcess = nullptr;

  if ((container.GetAnnihilationFlag() == "PostStep") &&
      (data.fTrackToSplit->GetKineticEnergy() > 0)) {
    emProcess = (GateGammaEmPostStepDoIt *)process;
  }
  if ((container.GetAnnihilationFlag() == "AtRest") ||
      (data.fTrackToSplit->GetKineticEnergy() == 0)) {
    eplusAnnihilProcess = (GateplusannihilAtRestDoIt *)process;
  }
  for (int j = 0; j < batchSize; j++) {
    G4int NbOfSecondaries = 0;
    G4int count = 0;
    while (NbOfSecondaries == 0) {
      if (process->GetProcessName() == "eBrem") {
        G4Track aTrack = eBremProcessFinalState(data.fTrackToSplit, initStep);
        bremProcess = (GateBremPostStepDoIt *)process;
        processFinalState =
            bremProcess->GateBremPostStepDoIt::PostStepDoIt(aTrack, *initStep);
      } else {
        if ((container.GetAnnihilationFlag() == "PostStep") &&
            (data.fTrackToSplit->GetKineticEnergy() > 0)) {
          processFinalState =
              emProcess->PostStepDoIt(*data.fTrackToSplit, *initStep);
        }
        if ((container.GetAnnihilationFlag() == "AtRest") ||
            (data.fTrackToSplit->GetKineticEnergy() == 0)) {
          processFinalState =
              eplusAnnihilProcess->GateplusannihilAtRestDoIt::AtRestDoIt(
                  *data.fTrackToSplit, *initStep);
        }
      }
      NbOfSecondaries = processFinalState->GetNumberOfSecondaries();
      if (NbOfSecondaries == 0) {
        processFinalState->Clear();
      }
      count++;
      // Security break, in case of infinite loop
      if (count > 10000) {
        G4ExceptionDescription ed;
        ed << " infinite loop detected during the track creation for the "
           << process->GetProcessName() << " process" << G4endl;
        G4Exception(
            "GateLastVertexInteractionSplittingActor::SecondariesSplitting",
            "BIAS.LV1", JustWarning, ed);
        G4RunManager::GetRunManager()->AbortEvent();
        data.fAbortedEvent = true;
        break;
      }
    }
    if (data.fAbortedEvent) {
      break;
    }
    G4bool IsPushBack = false;
    for (int i = 0; i < NbOfSecondaries; i++) {
      G4Track *newTrack = processFinalState->GetSecondary(i);
      G4ThreeVector momentum = newTrack->GetMomentumDirection();

      if (!(isnan(momentum[0]))) {
        if ((data.fAAManager != 0) &&
            (!(data.fAAManager->TestIfAccept(
                newTrack->GetPosition(), newTrack->GetMomentumDirection())))) {
          delete newTrack;
        } else if (IsPushBack == true) {
          delete newTrack;
        } else {
          newTrack->SetWeight(data.fWeight);
          newTrack->SetCreatorProcess(process);

          data.fStackManager->PushOneTrack(newTrack);

          IsPushBack = true;
        }
      } else {
        delete newTrack;
      }
    }
    processFinalState->Clear();
  }
}

void GateLastVertexInteractionSplittingActor::CreateNewParticleAtTheLastVertex(
    G4Step *initStep, LastVertexDataContainer theContainer,
    G4double batchSize) {
  auto &data = fWorkerState.Get();
  // We retrieve the process associated to the process name to split and we
  // split according the process. Since for compton scattering, the gamma is not
  // a secondary particles, this one need to have his own splitting function.

  G4String processName = data.fProcessNameToSplit;
  G4int nbOfTrackAlreadyInStack = data.fStackManager->GetNTotalTrack();
  if ((data.fProcessToSplit == 0) || (data.fProcessToSplit == nullptr)) {
    SimpleContainer container = theContainer.GetContainerToSplit();
    data.fProcessToSplit = GetProcessFromProcessName(
        container.GetParticleNameToSplit(), processName);
  }

  if (processName == "compt") {
    ComptonSplitting(initStep, data.fProcessToSplit, batchSize);
  }

  else if ((processName != "msc") && (processName != "conv")) {
    SecondariesSplitting(initStep, data.fProcessToSplit, theContainer,
                         batchSize);
  }
  data.fNumberOfTrackToSimulate =
      data.fStackManager->GetNTotalTrack() - nbOfTrackAlreadyInStack;
  data.fNbOfBatchForExitingParticle++;

  if ((data.fNumberOfTrackToSimulate == 0) && (data.fAbortedEvent == false)) {
    CreateNewParticleAtTheLastVertex(initStep, theContainer, batchSize);
  }
  if (data.fNbOfBatchForExitingParticle > fNbOfMaxBatchPerEvent) {
    data.fStackManager->clear();
    data.fRemovedParticle++;
  }
}

void GateLastVertexInteractionSplittingActor::FillOfDataTree(G4Step *step) {
  auto &data = fWorkerState.Get();

  G4String processName = "None";
  if (step->GetPostStepPoint()->GetProcessDefinedStep() != 0)
    processName =
        step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName();

  G4String creatorProcessName = "None";
  if (step->GetTrack()->GetCreatorProcess() != 0)
    creatorProcessName =
        step->GetTrack()->GetCreatorProcess()->GetProcessName();

  if ((step->GetTrack()->GetParticleDefinition()->GetParticleName() == "e+") &&
      ((step->GetTrack()->GetTrackStatus() == 1) ||
       (step->GetTrack()->GetTrackStatus() == 2))) {
    processName = "annihil";
  }

  G4String annihilFlag = "None";
  if (processName == "annihil") {
    if (step->GetPostStepPoint()->GetProcessDefinedStep() != 0) {
      if (processName ==
          step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName()) {
        annihilFlag = "PostStep";
      } else if (processName != step->GetPostStepPoint()
                                    ->GetProcessDefinedStep()
                                    ->GetProcessName()) {
        annihilFlag = "AtRest";
      }
    }
  }

  if (data.fIsFirstStep) {
    LastVertexDataContainer newContainer = LastVertexDataContainer();
    newContainer.SetTrackID(step->GetTrack()->GetTrackID());
    newContainer.SetParticleName(
        step->GetTrack()->GetDefinition()->GetParticleName());
    newContainer.SetCreationProcessName(creatorProcessName);

    if (data.fTree.empty()) {
      data.fTree.set_head(newContainer);
    }

    for (auto it = data.fTree.begin_post(); it != data.fTree.end_post(); ++it) {
      LastVertexDataContainer container = *it;
      G4int trackID = container.GetTrackID();

      if (step->GetTrack()->GetParentID() == trackID) {
        newContainer = container.ContainerFromParentInformation(step);
        data.fTree.append_child(it, newContainer);
        break;
      }
    }

    bool found = false;
    for (auto it = data.fTree.begin_post(); it != data.fTree.end_post(); ++it) {
      LastVertexDataContainer container = *it;
      G4int trackID = container.GetTrackID();
      if (step->GetTrack()->GetTrackID() == trackID) {
        data.fIterator = it;
        found = true;
        break;
      }
    }
    if (!found)
      Fatal("LastVertex: track " +
            std::to_string(step->GetTrack()->GetTrackID()) + " (parent " +
            std::to_string(step->GetTrack()->GetParentID()) +
            ") absent from genealogy tree");
  }

  LastVertexDataContainer *container = &(*data.fIterator);
  G4int trackID = container->GetTrackID();
  if ((processName != "Transportation") && (processName != "None") &&
      (processName != "Rayl")) {
    if (step->GetTrack()->GetTrackID() == trackID) {
      G4ThreeVector position = step->GetTrack()->GetPosition();
      G4ThreeVector prePosition = step->GetPreStepPoint()->GetPosition();
      G4ThreeVector momentum;
      if ((processName == "annihil"))
        momentum = step->GetPostStepPoint()->GetMomentumDirection();
      else {
        momentum = step->GetPreStepPoint()->GetMomentumDirection();
      }
      G4ThreeVector polarization = step->GetPreStepPoint()->GetPolarization();
      G4String particleName =
          step->GetTrack()->GetDefinition()->GetParticleName();
      G4double energy = step->GetPreStepPoint()->GetKineticEnergy();
      G4double weight = step->GetTrack()->GetWeight();
      G4int trackStatus = step->GetTrack()->GetTrackStatus();
      G4int nbOfSecondaries = step->GetfSecondary()->size();
      G4double stepLength = step->GetStepLength();
      G4TouchableHandle tch = step->GetTrack()->GetTouchableHandle();
      if (((processName == "annihil"))) {
        energy -= (step->GetTotalEnergyDeposit());
      }
      SimpleContainer containerToSplit =
          SimpleContainer(processName, energy, momentum, position, polarization,
                          particleName, weight, trackStatus, nbOfSecondaries,
                          annihilFlag, stepLength, prePosition, tch);
      container->SetContainerToSplit(containerToSplit);
      container->PushListOfSplittingParameters(containerToSplit);
    }
  }
}

G4bool GateLastVertexInteractionSplittingActor::IsParticleExitTheBiasedVolume(
    G4Step *step) {

  if ((step->GetPostStepPoint()->GetStepStatus() == 1)) {
    G4String logicalVolumeNamePostStep = "None";
    if (step->GetPostStepPoint()->GetPhysicalVolume() != 0)
      logicalVolumeNamePostStep = step->GetPostStepPoint()
                                      ->GetPhysicalVolume()
                                      ->GetLogicalVolume()
                                      ->GetName();

    if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(),
                  logicalVolumeNamePostStep) != fListOfVolumeAncestor.end()) {
      return true;
    }
  }
  if (step->GetPostStepPoint()->GetStepStatus() == 0)
    return true;
  return false;
}

G4bool GateLastVertexInteractionSplittingActor::
    IsTheParticleUndergoesALossEnergyProcess(G4Step *step) {
  if (step->GetPostStepPoint()->GetKineticEnergy() -
          step->GetPreStepPoint()->GetKineticEnergy() !=
      0)
    return true;
  return false;
}

void GateLastVertexInteractionSplittingActor::BeginOfRunAction(
    const G4Run *run) {
  auto &data = fWorkerState.Get();
  data.fSourceManager =
      const_cast<GateSourceManager *>(dynamic_cast<const GateSourceManager *>(
          G4RunManager::GetRunManager()->GetUserPrimaryGeneratorAction()));
  if (!data.fSourceManager)
    Fatal(
        "LastVertexSplitting requires the current worker's GateSourceManager");
  if (!fOnlyTree)
    data.fSourceManager->DeferRunCompletion();
  if (!data.fAAManager) {
    data.fAAManager = new GateAcceptanceAngleManager();
    data.fAAManager->Initialize(fAcceptanceAngleParameters, true);
  }

  data.fVertexSource = nullptr;
  for (auto *source : data.fSourceManager->fSources) {
    auto *replay = dynamic_cast<GateLastVertexSource *>(source);
    if (!replay)
      continue;
    if (data.fVertexSource)
      Fatal("LastVertexSplitting requires exactly one LastVertexSource; "
            "multiple replay sources are ambiguous");
    data.fVertexSource = replay;
  }
  if (!data.fVertexSource)
    Fatal("LastVertexSplitting requires exactly one LastVertexSource; none "
          "found");
  data.fStackManager = G4EventManager::GetEventManager()->GetStackManager();
}

void GateLastVertexInteractionSplittingActor::BeginOfEventAction(
    const G4Event *event) {
  auto &data = fWorkerState.Get();
  data.fActiveSource = data.fSourceManager->GetGeneratingSource();
  data.fEventID = event->GetEventID();
  data.fNumberOfEvent++;
  data.fIsAnnihilAlreadySplit = false;
  data.fAbortedEvent = false;
  data.fNbOfBatchForExitingParticle = 0;
  if (data.fEventID % 50000 == 0)
    std::cout << "event ID : " << data.fEventID << std::endl;
  if (data.fCopyInitStep != 0) {
    delete data.fCopyInitStep;
    data.fCopyInitStep = nullptr;
  }
  data.fSplitCounter = 0;
  data.fNumberOfTrackToSimulate = 0;
  data.fKilledBecauseOfProcess = false;

  if (data.fActiveSource == data.fVertexSource) {
    auto *vertexSource = data.fVertexSource;
    data.fContainer = vertexSource->GetLastVertexContainer();
    data.fProcessNameToSplit = vertexSource->GetProcessToSplit();
    if (data.fProcessToSplit != 0) {
      data.fProcessToSplit = nullptr;
    }
    if (data.fTrackToSplit != 0) {
      delete data.fTrackToSplit;
      data.fTrackToSplit = nullptr;
    }
    data.fTrackToSplit = CreateATrackFromContainer(data.fContainer);
    if (data.fTrackToSplit != 0)
      data.fWeight = data.fTrackToSplit->GetWeight() / fSplittingFactor;

    data.fNumberOfReplayedEvent++;
  }
}

void GateLastVertexInteractionSplittingActor::PreUserTrackingAction(
    const G4Track *track) {
  auto &data = fWorkerState.Get();
  data.fToSplit = true;
  data.fIsFirstStep = true;
}

void GateLastVertexInteractionSplittingActor::SteppingAction(G4Step *step) {
  auto &data = fWorkerState.Get();
  data.fAAManager->StartAcceptLoop();

  if (data.fActiveSource != data.fVertexSource) {
    FillOfDataTree(step);

    if (IsParticleExitTheBiasedVolume(step)) {
      if (data.fAAManager != 0) {
        if (data.fAAManager->TestIfAccept(
                step->GetTrack()->GetPosition(),
                step->GetTrack()->GetMomentumDirection())) {
          if ((*data.fIterator).GetContainerToSplit().GetProcessNameToSplit() !=
              "None") {
            data.fListOfContainer.push_back((*data.fIterator));
            data.fNumberOfReplayedParticle++;
          }
        }
      }
      step->GetTrack()->SetTrackStatus(fStopAndKill);
    }
  }

  if (fOnlyTree == false) {
    if (data.fActiveSource == data.fVertexSource) {

      if (data.fIsFirstStep) {
        data.fTrackID = step->GetTrack()->GetTrackID();
        data.fEkin = step->GetPostStepPoint()->GetKineticEnergy();
      } else {
        if ((data.fTrackID == step->GetTrack()->GetTrackID()) &&
            (data.fEkin != step->GetPreStepPoint()->GetKineticEnergy())) {
          data.fToSplit = false;
        } else {
          data.fEkin = step->GetPostStepPoint()->GetKineticEnergy();
        }
      }
      if (data.fToSplit) {
        G4String creatorProcessName = "None";
        if (step->GetTrack()->GetCreatorProcess() != 0)
          creatorProcessName =
              step->GetTrack()->GetCreatorProcess()->GetProcessName();
        if (((step->GetTrack()->GetParentID() == 0) &&
             (step->GetTrack()->GetTrackID() == 1)) ||
            ((creatorProcessName == "annihil") &&
             (step->GetTrack()->GetParentID() == 1))) {

          if ((data.fProcessNameToSplit != "annihil") ||
              ((data.fProcessNameToSplit == "annihil") &&
               (data.fIsAnnihilAlreadySplit == false))) {

            // FIXME : list of process which are not splitable yet

            if ((data.fProcessNameToSplit != "msc") &&
                (data.fProcessNameToSplit != "conv") &&
                (data.fProcessNameToSplit != "eIoni") &&
                (((data.fProcessNameToSplit != "phot") ||
                  ((data.fProcessNameToSplit == "phot") &&
                   (step->GetTrack()
                        ->GetParticleDefinition()
                        ->GetParticleName() != "gamma"))))) {
              delete data.fCopyInitStep;
              data.fCopyInitStep = new G4Step(*step);
              if (data.fProcessNameToSplit == "eBrem") {
                data.fCopyInitStep->SetStepLength(
                    data.fContainer.GetContainerToSplit().GetStepLength());
                data.fCopyInitStep->GetPreStepPoint()->SetKineticEnergy(
                    data.fContainer.GetContainerToSplit().GetEnergy());
              }
              CreateNewParticleAtTheLastVertex(data.fCopyInitStep,
                                               data.fContainer, fBatchSize);
            }

            step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);

            if (data.fProcessNameToSplit == "annihil") {
              data.fIsAnnihilAlreadySplit = true;
            }
          }

          else if ((data.fProcessNameToSplit == "annihil") &&
                   (data.fIsAnnihilAlreadySplit == true)) {
            step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
          }

        }

        else {
          if (data.fIsFirstStep) {
            data.fNumberOfTrackToSimulate--;

            if (data.fKilledBecauseOfProcess == false) {
              data.fSplitCounter += 1;
            } else {
              data.fKilledBecauseOfProcess = false;
            }

            if (data.fSplitCounter > fSplittingFactor) {
              step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
              data.fStackManager->clear();
            }
          }

          if (IsTheParticleUndergoesALossEnergyProcess(step)) {
            step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
            data.fKilledBecauseOfProcess = true;
          }

          if (data.fIsFirstStep) {
            if (data.fSplitCounter <= fSplittingFactor) {
              if (data.fNumberOfTrackToSimulate == 0) {
                CreateNewParticleAtTheLastVertex(data.fCopyInitStep,
                                                 data.fContainer, fBatchSize);
              }
            }
          }
        }
      }
    }
  }

  data.fIsFirstStep = false;
}

void GateLastVertexInteractionSplittingActor::EndOfEventAction(
    const G4Event *event) {
  auto &data = fWorkerState.Get();
  if (data.fActiveSource == nullptr)
    return; // synthetic event: preserve pending replay state for the stop check

  if (data.fActiveSource != data.fVertexSource) {

    data.fVertexSource->SetNumberOfEventToSimulate(
        data.fListOfContainer.size());
    data.fVertexSource->SetNumberOfGeneratedEvent(0);
    data.fVertexSource->SetListOfVertexToSimulate(data.fListOfContainer);
    data.fTree.clear();
    data.fListOfContainer.clear();
  }

  if (fOnlyTree == false) {

    auto *vertexSource = data.fVertexSource;
    if (vertexSource->GetNumberOfGeneratedEvent() <
        vertexSource->GetNumberOfEventToSimulate()) {
      data.fSourceManager->SetActiveSource(vertexSource);
    }
  }
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateLastVertexInteractionSplittingActor::WorkerState::~WorkerState() {
  ReleaseResources();
}

void GateLastVertexInteractionSplittingActor::WorkerState::ReleaseResources() {
  delete fCopyInitStep;
  fCopyInitStep = nullptr;
  delete fTrackToSplit;
  fTrackToSplit = nullptr;
  if (fAAManager) {
    for (auto *tester : fAAManager->fAATesters)
      delete tester;
    delete fAAManager;
    fAAManager = nullptr;
  }
}

void GateLastVertexInteractionSplittingActor::StartSimulationAction() {
  fRemovedParticle = 0;
  fNumberOfReplayedParticle = 0;
  fNumberOfReplayedEvent = 0;
  fNumberOfEvent = 0;
}

void GateLastVertexInteractionSplittingActor::EndOfSimulationWorkerAction(
    const G4Run *) {
  auto &data = fWorkerState.Get();
  // Same reduction pattern as SimulationStatisticsActor: no per-event lock.
  G4AutoLock lock(&SetEventCorrectionForLastVertex);
  fRemovedParticle += data.fRemovedParticle;
  fNumberOfReplayedParticle += data.fNumberOfReplayedParticle;
  fNumberOfReplayedEvent += data.fNumberOfReplayedEvent;
  fNumberOfEvent += data.fNumberOfEvent;
  data.fRemovedParticle = 0;
  data.fNumberOfReplayedParticle = 0;
  data.fNumberOfReplayedEvent = 0;
  data.fNumberOfEvent = 0;
  lock.unlock();
  // Release worker-owned physics/geometry objects before Geant4 teardown.
  data.ReleaseResources();
}
