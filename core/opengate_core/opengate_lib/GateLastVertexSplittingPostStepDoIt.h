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
#ifndef GateLastVertexSplittingPostStepDoIt_h
#define GateLastVertexSplittingPostStepDoIt_h


#include "G4VEnergyLossProcess.hh"
#include "G4VEmProcess.hh"
#include "G4VParticleChange.hh"
#include "G4eplusAnnihilation.hh"
#include "G4PhysicalConstants.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4Gamma.hh"
#include "G4Electron.hh"
#include "G4Positron.hh"
#include "G4eeToTwoGammaModel.hh"
#include "G4EmBiasingManager.hh"
#include "G4EntanglementAuxInfo.hh"
#include "G4eplusAnnihilationEntanglementClipBoard.hh"
#include "G4EmParameters.hh"
#include "G4PhysicsModelCatalog.hh"
#include <iostream>




class GateBremPostStepDoIt : public G4VEnergyLossProcess {
public :

GateBremPostStepDoIt();

~ GateBremPostStepDoIt();

virtual G4VParticleChange * PostStepDoIt (const G4Track & track, const G4Step &  step) override 
{
  const G4MaterialCutsCouple* couple = step.GetPreStepPoint()->GetMaterialCutsCouple();
  currentCouple = couple;
  G4VParticleChange* particleChange = G4VEnergyLossProcess::PostStepDoIt(track,step);
  return particleChange;
}


};


class GateGammaEmPostStepDoIt : public G4VEmProcess {
public :

GateGammaEmPostStepDoIt();

~ GateGammaEmPostStepDoIt();

virtual G4VParticleChange * PostStepDoIt(const G4Track & track, const G4Step & step) override 
{
  const G4MaterialCutsCouple* couple = step.GetPreStepPoint()->GetMaterialCutsCouple();
  
  std::cout<<track.GetDefinition()->GetParticleName()<<std::endl;
  G4VParticleChange* particleChange = G4VEmProcess::PostStepDoIt(track,step);
  std::cout<<track.GetDefinition()->GetParticleName()<<std::endl;
  return particleChange;
}


};

class GateplusannihilAtRestDoIt : public G4eplusAnnihilation {
public :

GateplusannihilAtRestDoIt();
~ GateplusannihilAtRestDoIt();

virtual G4VParticleChange* AtRestDoIt(const G4Track& track,
						   const G4Step& step) override
// Performs the e+ e- annihilation when both particles are assumed at rest.
  {
    fParticleChange.InitializeForPostStep(track);
    DefineMaterial(step.GetPreStepPoint()->GetMaterialCutsCouple());
    G4int idx = (G4int)CurrentMaterialCutsCoupleIndex();
    G4double ene(0.0);
    G4VEmModel* model = SelectModel(ene, idx);

    // define new weight for primary and secondaries
    G4double weight = fParticleChange.GetParentWeight();

    // sample secondaries
    secParticles.clear();
    G4double gammaCut = GetGammaEnergyCut();
    model->SampleSecondaries(&secParticles, MaterialCutsCouple(), 
          track.GetDynamicParticle(), gammaCut);

    G4int num0 = (G4int)secParticles.size();
    // splitting or Russian roulette
    if(biasManager) {
      if(biasManager->SecondaryBiasingRegion(idx)) {
        G4double eloss = 0.0;
        weight *= biasManager->ApplySecondaryBiasing(
    secParticles, track, model, &fParticleChange, eloss, 
          idx, gammaCut, step.GetPostStepPoint()->GetSafety());
        if(eloss > 0.0) {
          eloss += fParticleChange.GetLocalEnergyDeposit();
          fParticleChange.ProposeLocalEnergyDeposit(eloss);
        }
      }
    }

    // save secondaries
    G4int num = (G4int)secParticles.size();

    // Check that entanglement is switched on... (the following flag is
    // set by /process/em/QuantumEntanglement).
    G4bool entangled = G4EmParameters::Instance()->QuantumEntanglement();
    // ...and that we have two gammas with both gammas' energies above
    // gammaCut (entanglement is only programmed for e+ e- -> gamma gamma).
    G4bool entangledgammagamma = false;
    if (entangled) {
      if (num == 2) {
        entangledgammagamma = true;
        for (const auto* p: secParticles) {
          if (p->GetDefinition() != G4Gamma::Gamma() ||
              p->GetKineticEnergy() < gammaCut) {
            entangledgammagamma = false;
          }
        }
      }
    }

    // Prepare a shared pointer for psossible use below. If it is used, the
    // shared pointer is copied into the tracks through G4EntanglementAuxInfo.
    // This ensures the clip board lasts until both tracks are destroyed.
    std::shared_ptr<G4eplusAnnihilationEntanglementClipBoard> clipBoard;
    if (entangledgammagamma) {
      clipBoard = std::make_shared<G4eplusAnnihilationEntanglementClipBoard>();
      clipBoard->SetParentParticleDefinition(track.GetDefinition());
    }

    if(num > 0) {
      fParticleChange.SetNumberOfSecondaries(num);
      G4double edep = fParticleChange.GetLocalEnergyDeposit();
      G4double time = track.GetGlobalTime();
      
      for (G4int i=0; i<num; ++i) {
        if (secParticles[i]) {
          G4DynamicParticle* dp = secParticles[i];
          const G4ParticleDefinition* p = dp->GetParticleDefinition();
          G4double e = dp->GetKineticEnergy();
          G4bool good = true;
          if(ApplyCuts()) {
            if (p == G4Gamma::Gamma()) {
              if (e < gammaCut) { good = false; }
            } else if (p == G4Electron::Electron()) {
              if (e < GetElectronEnergyCut()) { good = false; }
            }
            // added secondary if it is good
          }
          if (good) { 
            G4Track* t = new G4Track(dp, time, track.GetPosition());
            t->SetTouchableHandle(track.GetTouchableHandle());
            if (entangledgammagamma) {
        // entangledgammagamma is only true when there are only two gammas
        // (See code above where entangledgammagamma is calculated.)
              if (i == 0) { // First gamma
                clipBoard->SetTrackA(t);
              } else if (i == 1) {  // Second gamma
                clipBoard->SetTrackB(t);
              }
              t->SetAuxiliaryTrackInformation
              (G4PhysicsModelCatalog::GetModelID("model_GammaGammaEntanglement"),new G4EntanglementAuxInfo(clipBoard));
            }
            if (biasManager) {
              t->SetWeight(weight * biasManager->GetWeight(i));
            } else {
              t->SetWeight(weight);
            }
            pParticleChange->AddSecondary(t);

            // define type of secondary
            if(i < mainSecondaries) { t->SetCreatorModelID(secID); }
            else if(i < num0) {
              if(p == G4Gamma::Gamma()) { 
                t->SetCreatorModelID(fluoID);
              } else {
                t->SetCreatorModelID(augerID);
        }
      } else {
              t->SetCreatorModelID(biasID);
            }
            /* 
            G4cout << "Secondary(post step) has weight " << t->GetWeight() 
                  << ", Ekin= " << t->GetKineticEnergy()/MeV << " MeV "
                  << GetProcessName() << " fluoID= " << fluoID
                  << " augerID= " << augerID <<G4endl;
            */
          } else {
            delete dp;
            edep += e;
          }
        } 
      }
      fParticleChange.ProposeLocalEnergyDeposit(edep);
    }
    return &fParticleChange;
  }
};
#endif
