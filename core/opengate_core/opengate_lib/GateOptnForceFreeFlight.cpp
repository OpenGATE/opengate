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
#include "GateOptnForceFreeFlight.h"
#include "G4ILawForceFreeFlight.hh"
#include "G4BiasingProcessInterface.hh"
#include "G4Step.hh"



// This operator is used to transport the particle without interaction, and then correct the weight of the particle
//according to the probablity for the photon to not interact within the matter. To do that, we use a GEANT4 modifed Interaction Law (G4ILawForceFreeFlight), which modify,
//for the biased process the probability for the interaction to occur :  Never.  
//This occurence is called during the tracking for each step. Here the step is the largest possible, and one step correspond to the path of
//particle in the media.

GateOptnForceFreeFlight ::GateOptnForceFreeFlight (G4String name)
  : G4VBiasingOperation    ( name ),
    fOperationComplete     ( true )
{
  fForceFreeFlightInteractionLaw = new G4ILawForceFreeFlight("LawForOperation"+name);
}

GateOptnForceFreeFlight ::~GateOptnForceFreeFlight ()
{
  if ( fForceFreeFlightInteractionLaw ) delete fForceFreeFlightInteractionLaw;
}



const G4VBiasingInteractionLaw* GateOptnForceFreeFlight ::ProvideOccurenceBiasingInteractionLaw
( const G4BiasingProcessInterface*, G4ForceCondition& proposeForceCondition )
{
  fOperationComplete = false;
  proposeForceCondition = Forced;
  return fForceFreeFlightInteractionLaw;
}

G4VParticleChange* GateOptnForceFreeFlight ::ApplyFinalStateBiasing( const G4BiasingProcessInterface* callingProcess,
								   const G4Track* track,
								   const G4Step* step,
								   G4bool& forceFinalState)
{


  fParticleChange.Initialize( *track );
  forceFinalState    = true;
  fCountProcess ++;

    fProposedWeight *= fWeightChange[callingProcess->GetWrappedProcess()->GetProcessName()];      
    if (fUseProbes){
      if (track->IsGoodForTracking() ==0){ 
                                                    
        if (fProposedWeight < fRussianRouletteProbability * fMinWeight){
          fParticleChange.ProposeTrackStatus(G4TrackStatus::fStopAndKill);
          return &fParticleChange;
        }

        if ((fProposedWeight < fMinWeight) && (fProposedWeight >=  fRussianRouletteProbability * fMinWeight)) {
          G4double probability = G4UniformRand();
          if (probability > fRussianRouletteProbability){
            fParticleChange.ProposeTrackStatus(G4TrackStatus::fStopAndKill);
            return &fParticleChange;
          }
          else {
            fProposedWeight = fProposedWeight/fRussianRouletteProbability;
          }
        }

        fParticleChange.ProposeWeight(fProposedWeight);
        fOperationComplete = true;
      }
        if (track->IsGoodForTracking() ==1){
          fParticleChange.ProposeWeight(fProposedWeight);
          fOperationComplete = true;
      }
  }
  else {                               
      if ((fProposedWeight < fRussianRouletteProbability * fMinWeight)|| ((fProposedWeight < fMinWeight) && (fSurvivedToRR == true))) {
        fParticleChange.ProposeTrackStatus(G4TrackStatus::fStopAndKill);
        return &fParticleChange;
      }

      if ((fProposedWeight < fMinWeight) && (fProposedWeight >=  fRussianRouletteProbability * fMinWeight) && (fCountProcess == 4) && (fSurvivedToRR == false)) {
        G4double probability = G4UniformRand();
        
        if (probability > fRussianRouletteProbability){
          fParticleChange.ProposeTrackStatus(G4TrackStatus::fStopAndKill);
          return &fParticleChange;
        }
        else {
          fProposedWeight = fProposedWeight/fRussianRouletteProbability;
          //std::cout<<"lim "<< fMinWeight << " RR  " <<fRussianRouletteProbability<< " weight  " <<fProposedWeight<<std::endl;
          fSurvivedToRR = true;
        }
      }
      fParticleChange.ProposeWeight(fProposedWeight);
      fOperationComplete = true;
  }
return &fParticleChange;
}

void GateOptnForceFreeFlight ::AlongMoveBy( const G4BiasingProcessInterface* callingProcess, const G4Step*, G4double weightChange )

{
  fWeightChange[callingProcess->GetWrappedProcess()->GetProcessName()] = weightChange;
}
