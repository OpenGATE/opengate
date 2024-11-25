/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateKillAccordingProcessesActor.h"
#include "G4LogicalVolumeStore.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4ProcessManager.hh"
#include "G4VProcess.hh"
#include "G4ios.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

G4Mutex SetNbKillAccordingProcessesMutex = G4MUTEX_INITIALIZER;

GateKillAccordingProcessesActor::GateKillAccordingProcessesActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {}

std::vector<G4String>
GateKillAccordingProcessesActor::GetListOfPhysicsListProcesses() {
  std::vector<G4String> listOfAllProcesses = {};

  G4ParticleTable *particleTable = G4ParticleTable::GetParticleTable();

  for (G4int i = 0; i < particleTable->size(); ++i) {
    G4ParticleDefinition *particle = particleTable->GetParticle(i);
    G4String particleName = particle->GetParticleName();
    G4ProcessManager *processManager = particle->GetProcessManager();
    if (!processManager)
      continue;
    G4int numProcesses = processManager->GetProcessListLength();
    for (G4int j = 0; j < numProcesses; ++j) {
      const G4VProcess *process = (*(processManager->GetProcessList()))[j];
      G4String processName = process->GetProcessName();
      if (std::find(listOfAllProcesses.begin(), listOfAllProcesses.end(),
                    processName) == listOfAllProcesses.end())
        listOfAllProcesses.push_back(processName);
    }
  }
  return listOfAllProcesses;
}

void GateKillAccordingProcessesActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fProcessesToKill = DictGetVecStr(user_info, "processes_to_kill");
  fIsRayleighAnInteraction =
      DictGetBool(user_info, "is_rayleigh_an_interaction");
}

void GateKillAccordingProcessesActor::BeginOfRunAction(const G4Run *run) {
  fNbOfKilledParticles = 0;
  std::vector<G4String> listOfAllProcesses = GetListOfPhysicsListProcesses();
  listOfAllProcesses.push_back("all");
  for (auto process : fProcessesToKill) {
    if (std::find(listOfAllProcesses.begin(), listOfAllProcesses.end(),
                  process) == listOfAllProcesses.end()) {
      G4String errorMessage =
          "Process '" + process + "' not found. Existing processes are '";
      for (auto aProcess : listOfAllProcesses) {
        errorMessage = errorMessage + aProcess + "', ";
      }
      errorMessage.pop_back();
      errorMessage.pop_back();
      G4Exception("CheckProcessExistence", // Exception origin
                  "ProcessNotFound.1",     // Exception code
                  FatalException,          // Exception severity
                  errorMessage);
    }
  }
  if (fProcessesToKill[0] == "all") {
    if (fProcessesToKill.size() == 1) {
      fKillIfAnyInteraction = true;
    }
  }
}

void GateKillAccordingProcessesActor::PreUserTrackingAction(
    const G4Track *track) {
  fIsFirstStep = true;
}

void GateKillAccordingProcessesActor::SteppingAction(G4Step *step) {

  G4String logNameMotherVolume = G4LogicalVolumeStore::GetInstance()
                                     ->GetVolume(fAttachedToVolumeName)
                                     ->GetName();
  G4String physicalVolumeNamePreStep = "None";

  G4String processName = "None";
  const G4VProcess *process = step->GetPostStepPoint()->GetProcessDefinedStep();
  if (process != 0)
    processName = process->GetProcessName();

  // Positron exception to retrieve the annihilation process, since it's an at
  // rest process most of the time

  if ((step->GetTrack()->GetParticleDefinition()->GetParticleName() == "e+") &&
      (step->GetTrack()->GetTrackStatus() == 1))
    processName = "annihil";

  if (fKillIfAnyInteraction) {
    if (processName != "Transportation") {
      if (fIsRayleighAnInteraction == true) {
        step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
        G4AutoLock mutex(&SetNbKillAccordingProcessesMutex);
        fNbOfKilledParticles++;
      } else {
        if (processName != "Rayl") {
          step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
          G4AutoLock mutex(&SetNbKillAccordingProcessesMutex);
          fNbOfKilledParticles++;
        }
      }
    }
  } else {
    if (std::find(fProcessesToKill.begin(), fProcessesToKill.end(),
                  processName) != fProcessesToKill.end()) {
      step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
      G4AutoLock mutex(&SetNbKillAccordingProcessesMutex);
      fNbOfKilledParticles++;
    }
  }
}
