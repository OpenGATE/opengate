/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateKillAccordingProcessesActor.h"
#include "G4LogicalVolumeStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4ios.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "G4VProcess.hh"
#include "G4ProcessManager.hh"
#include "G4ParticleTable.hh"






GateKillAccordingProcessesActor::GateKillAccordingProcessesActor(
    py::dict &user_info)
    : GateVActor(user_info, false) {

}


std::vector<G4String> GateKillAccordingProcessesActor::GetListOfPhysicsListProcesses(){
std::vector<G4String> listOfAllProcesses = {};

G4ParticleTable* particleTable = G4ParticleTable::GetParticleTable();
    
    for (G4int i = 0; i < particleTable->size(); ++i) {
        G4ParticleDefinition* particle = particleTable->GetParticle(i);
        G4String particleName = particle->GetParticleName();
        G4ProcessManager* processManager = particle->GetProcessManager();
        if (!processManager) continue;
        G4int numProcesses = processManager->GetProcessListLength();
        for (G4int j = 0; j < numProcesses; ++j) {
            const G4VProcess* process = (*(processManager->GetProcessList()))[j];
            G4String processName = process->GetProcessName();
            if (std::find(listOfAllProcesses.begin(),listOfAllProcesses.end(),processName) == listOfAllProcesses.end())
              listOfAllProcesses.push_back(processName);
        }
    }
return listOfAllProcesses;
}


void GateKillAccordingProcessesActor::InitializeUserInput(py::dict &user_info) {
GateVActor::InitializeUserInput(user_info);
fProcessesToKillIfOccurence =  DictGetVecStr(user_info,"processes_to_kill_if_occurence");
fProcessesToKillIfNoOccurence =  DictGetVecStr(user_info,"processes_to_kill_if_no_occurence");

}

void GateKillAccordingProcessesActor::BeginOfRunAction(const G4Run* run) {
  fNbOfKilledParticles = 0;
  std::vector<G4String> listOfAllProcesses = GetListOfPhysicsListProcesses();
  for (auto process:fProcessesToKillIfOccurence) {
    if (std::find(listOfAllProcesses.begin(),listOfAllProcesses.end(),process) == listOfAllProcesses.end()){
       G4String errorMessage = "Process '" +process + "' not found. Existing processes are '";
       for (auto aProcess:listOfAllProcesses){
        errorMessage  = errorMessage + aProcess + "', ";
       }
       errorMessage.pop_back();
       errorMessage.pop_back();
            G4Exception("CheckProcessExistence",              // Exception origin
                        "ProcessNotFound.1",                    // Exception code
                        FatalException,                       // Exception severity
                        errorMessage);  
    }
    
  }
  for (auto process:fProcessesToKillIfNoOccurence) {
    if (std::find(listOfAllProcesses.begin(),listOfAllProcesses.end(),process) == listOfAllProcesses.end()){
       G4String errorMessage = "Process '" +process + "' not found. Existing processes are '";
       for (auto aProcess:listOfAllProcesses){
        errorMessage  = errorMessage + aProcess + "', ";
       }
       errorMessage.pop_back();
       errorMessage.pop_back();
            G4Exception("CheckProcessExistence",              // Exception origin
                        "ProcessNotFound.2",                    // Exception code
                        FatalException,                       // Exception severity
                        errorMessage);  
    }
    
  }

  
}

void GateKillAccordingProcessesActor::PreUserTrackingAction(
    const G4Track *track) {
  fIsFirstStep = true;
}

void GateKillAccordingProcessesActor::SteppingAction(G4Step *step) {
  

  G4String logNameMotherVolume = G4LogicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName)->GetName();
  G4String physicalVolumeNamePreStep = "None";
  if (step->GetPreStepPoint()->GetPhysicalVolume() !=0)                                
    physicalVolumeNamePreStep = step->GetPreStepPoint()->GetPhysicalVolume()->GetName();
  if (((step->GetTrack()->GetLogicalVolumeAtVertex()->GetName() != logNameMotherVolume) && (fIsFirstStep)) || ((fIsFirstStep) && (step->GetTrack()->GetParentID() == 0))) {
    if (((step->GetPreStepPoint()->GetStepStatus() == 1) && (physicalVolumeNamePreStep == fMotherVolumeName)) || ((fIsFirstStep) && (step->GetTrack()->GetParentID() == 0))) {
      fKill = true;
    }
  }


  G4String processName = "None";
  const G4VProcess* process = step->GetPostStepPoint()->GetProcessDefinedStep();
  if (process != 0)
    processName = process->GetProcessName();

  //Positron exception to retrieve the annihilation process, since it's an at rest process most of the time 

  if ((step->GetTrack()->GetParticleDefinition()->GetParticleName() == "e+") && (step->GetTrack()->GetTrackStatus() == 1))
    processName ="annihil";

  if (std::find(fProcessesToKillIfNoOccurence.begin(),fProcessesToKillIfNoOccurence.end(),processName) != fProcessesToKillIfNoOccurence.end()){
    fKill = false;
  }


 G4String logicalVolumeNamePostStep = step->GetPostStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();
 if (step->GetPostStepPoint()->GetStepStatus() == 1) {
    if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(), logicalVolumeNamePostStep) != fListOfVolumeAncestor.end()) {
      if (fKill == true){
        step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
        fNbOfKilledParticles++;
      }
      }
    }

  if (std::find(fProcessesToKillIfOccurence.begin(),fProcessesToKillIfOccurence.end(),processName) !=fProcessesToKillIfOccurence.end())
  {
    step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
    fNbOfKilledParticles++;
  }
  else {
     if (step->GetTrack()->GetTrackStatus() == 3)
        fKill=true;
  }


  



}
