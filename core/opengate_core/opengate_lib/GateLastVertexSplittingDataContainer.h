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
///
#ifndef LastVertexDataContainer_h
#define LastVertexDataContainer_h

#include "G4Electron.hh"
#include "G4EmBiasingManager.hh"
#include "G4EmParameters.hh"
#include "G4EntanglementAuxInfo.hh"
#include "G4Gamma.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4PhysicalConstants.hh"
#include "G4PhysicsModelCatalog.hh"
#include "G4Positron.hh"
#include "G4Track.hh"
#include "G4VEmProcess.hh"
#include "G4VEnergyLossProcess.hh"
#include "G4VParticleChange.hh"
#include "G4eeToTwoGammaModel.hh"
#include "G4eplusAnnihilation.hh"
#include "G4eplusAnnihilationEntanglementClipBoard.hh"
#include "GateLastVertexSplittingSimpleContainer.h"
#include <iostream>

class LastVertexDataContainer {

public:
  LastVertexDataContainer() {}

  ~LastVertexDataContainer() {}

  void SetTrackID(G4int trackID) { fTrackID = trackID; }

  G4int GetTrackID() { return fTrackID; }

  void SetParticleName(G4String name) { fParticleName = name; }

  G4String GetParticleName() { return fParticleName; }

  void SetCreationProcessName(G4String creationProcessName) {
    fCreationProcessName = creationProcessName;
  }

  G4String GetCreationProcessName() { return fCreationProcessName; }

  void SetContainerToSplit(SimpleContainer container) {
    fContainerToSplit = container;
  }

  SimpleContainer GetContainerToSplit() { return fContainerToSplit; }

  void PushListOfSplittingParameters(SimpleContainer container) {
    fVectorOfContainerToSplit.emplace_back(container);
  }

  LastVertexDataContainer ContainerFromParentInformation(G4Step *step) {
    LastVertexDataContainer aContainer = LastVertexDataContainer();

    aContainer.fTrackID = step->GetTrack()->GetTrackID();
    aContainer.fParticleName =
        step->GetTrack()->GetDefinition()->GetParticleName();
    if (this->fContainerToSplit.GetProcessNameToSplit() != "None") {
      if (this->fVectorOfContainerToSplit.size() != 0) {
        G4ThreeVector vertexPosition = step->GetTrack()->GetVertexPosition();
        for (int i = 0; i < this->fVectorOfContainerToSplit.size(); i++) {
          if (vertexPosition ==
              this->fVectorOfContainerToSplit[i].GetVertexPosition()) {
            SimpleContainer tmpContainer = this->fVectorOfContainerToSplit[i];
            // std::cout<<"1 "<<tmpContainer.GetProcessNameToSplit()<<std::endl;
            aContainer.fContainerToSplit = SimpleContainer(
                tmpContainer.GetProcessNameToSplit(), tmpContainer.GetEnergy(),
                tmpContainer.GetMomentum(), tmpContainer.GetVertexPosition(),
                tmpContainer.GetPolarization(),
                tmpContainer.GetParticleNameToSplit(), tmpContainer.GetWeight(),
                tmpContainer.GetTrackStatus(),
                tmpContainer.GetNbOfSecondaries(),
                tmpContainer.GetAnnihilationFlag(),
                tmpContainer.GetStepLength(),
                tmpContainer.GetPrePositionToSplit());
            return aContainer;
          }
        }
      } else {
        SimpleContainer tmpContainer = this->fContainerToSplit;
        // std::cout<<"2  "<<tmpContainer.GetProcessNameToSplit()<<std::endl;
        aContainer.fContainerToSplit = SimpleContainer(
            tmpContainer.GetProcessNameToSplit(), tmpContainer.GetEnergy(),
            tmpContainer.GetMomentum(), tmpContainer.GetVertexPosition(),
            tmpContainer.GetPolarization(),
            tmpContainer.GetParticleNameToSplit(), tmpContainer.GetWeight(),
            tmpContainer.GetTrackStatus(), tmpContainer.GetNbOfSecondaries(),
            tmpContainer.GetAnnihilationFlag(), tmpContainer.GetStepLength(),
            tmpContainer.GetPrePositionToSplit());
        return aContainer;
      }
    }
    // std::cout<<"3"<<std::endl;
    return aContainer;
  }

  friend std::ostream &operator<<(std::ostream &os,
                                  LastVertexDataContainer &container) {
    os << container.fParticleName << " ID: " << container.fTrackID
       << " process to split : "
       << container.fContainerToSplit.GetProcessNameToSplit()
       << " name to split"
       << container.fContainerToSplit.GetParticleNameToSplit();
    return os;
  }

private:
  G4String fParticleName = "None";
  G4int fTrackID = 0;
  G4String fCreationProcessName = "None";
  SimpleContainer fContainerToSplit;

  std::vector<SimpleContainer> fVectorOfContainerToSplit;
};

#endif
