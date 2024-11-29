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
//
// ---------------------------------------------------------------
//
// GateOptrForceCollision
//
// Class Description:
//    A G4VBiasingOperator that implements a "force collision" a la
// MCNP. This is meant for neutral particles.
//    When the track enters the volume, it is cloned. One copy makes
// a forced free flight up to the volume exit. The other copy makes
// a forced collision inside the volume.
//
// ---------------------------------------------------------------
//   Initial version                         Nov. 2013 M. Verderi


#ifndef GateOptrForceCollision_h
#define GateOptrForceCollision_h 1

#include "G4VBiasingOperator.hh"
class GateOptnForceFreeFlight;
class GateOptnForceCommonTruncatedExp;
class GateOptnCloning;
class G4VProcess;
class G4BiasingProcessInterface;
class G4ParticleDefinition;
#include <vector>
#include <map>
#include "G4ThreeVector.hh"
#include "GateVActor.h"
class GateOptrForceCollisionTrackData;

class GateOptrForceCollision : public G4VBiasingOperator,public GateVActor {
public:
  GateOptrForceCollision(py::dict &user_info);
  ~GateOptrForceCollision();
  
public:
  // -- Mandatory from base class :
  virtual G4VBiasingOperation* ProposeNonPhysicsBiasingOperation(const G4Track* track, const G4BiasingProcessInterface* callingProcess) final;
  virtual G4VBiasingOperation*  ProposeOccurenceBiasingOperation(const G4Track* track, const G4BiasingProcessInterface* callingProcess) final;
  virtual G4VBiasingOperation* ProposeFinalStateBiasingOperation(const G4Track* track, const G4BiasingProcessInterface* callingProcess) final;
  // -- optional methods from base class:
public:
  virtual void           Configure() final;
  virtual void  ConfigureForWorker() final;
  virtual void            StartRun() final;
  virtual void       StartTracking( const G4Track* track ) final;
  virtual void         ExitBiasing( const G4Track*, const G4BiasingProcessInterface* ) final {};
  virtual void         EndTracking() final;
  void InitializeUserInfo(py::dict &user_info) override;

void AttachAllLogicalDaughtersVolumes(G4LogicalVolume *volume);

  // -- operation applied:
  void OperationApplied( const G4BiasingProcessInterface*            callingProcess, G4BiasingAppliedCase                      biasingCase,
			 G4VBiasingOperation*                      operationApplied, const G4VParticleChange*        particleChangeProduced ) final;
  void OperationApplied( const G4BiasingProcessInterface*            callingProcess, G4BiasingAppliedCase                      biasingCase,
  			 G4VBiasingOperation*             occurenceOperationApplied, G4double                 weightForOccurenceInteraction,
  			 G4VBiasingOperation*            finalStateOperationApplied, const G4VParticleChange*        particleChangeProduced ) final;
  

const G4String GetName(){
  return GateVActor::GetName();
}

public:
  G4int                                      fForceCollisionModelID;
  const G4Track*                                      fCurrentTrack;
  GateOptrForceCollisionTrackData*                 fCurrentTrackData;
  std::map< const G4BiasingProcessInterface*, GateOptnForceFreeFlight* > fFreeFlightOperations;
  GateOptnForceCommonTruncatedExp*  fSharedForceInteractionOperation;
  GateOptnCloning*                                 fCloningOperation;
  G4double                                      fInitialTrackWeight;
  G4bool                                                     fSetup;
  const G4ParticleDefinition*                       fParticleToBias;
};

#endif
