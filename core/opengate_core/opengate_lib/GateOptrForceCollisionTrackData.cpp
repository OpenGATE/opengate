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
#include "GateOptrForceCollisionTrackData.h"
#include "GateOptrForceCollision.h"

GateOptrForceCollisionTrackData::GateOptrForceCollisionTrackData( const GateOptrForceCollision* optr )
: G4VAuxiliaryTrackInformation(),
  fForceCollisionOperator( optr )
{
  fForceCollisionState = ForceCollisionState::free;
}

GateOptrForceCollisionTrackData::~GateOptrForceCollisionTrackData()
{
  if ( fForceCollisionState != ForceCollisionState::free )
    {
      G4ExceptionDescription ed;
      ed << "Track deleted while under G4BOptrForceCollision biasing scheme of operator `";
      if ( fForceCollisionOperator == nullptr ) ed << "(none)"; else ed << "forceCollisionActor";
      ed <<"'. Will result in inconsistencies.";
      G4Exception(" GateOptrForceCollisionTrackData::~GateOptrForceCollisionTrackData()",
		  "BIAS.GEN.19",
		  JustWarning,
		  ed);
    }
}

void GateOptrForceCollisionTrackData::Print() const
{
  G4cout << " GateOptrForceCollisionTrackData object : " << this << G4endl;
  G4cout << "     Force collision operator : "; if ( fForceCollisionOperator == nullptr ) G4cout << "(none)"; else G4cout << "forceCollisionActor"; G4cout << G4endl;
  G4cout << "     Force collision state    : ";
  switch ( fForceCollisionState )
    {
    case ForceCollisionState::free :
      G4cout << "free from biasing ";
      break;
    case ForceCollisionState::toBeCloned :
      G4cout << "to be cloned ";
      break;
    case ForceCollisionState::toBeForced :
      G4cout << "to be interaction forced ";
      break;
    case ForceCollisionState::toBeFreeFlight :
      G4cout << "to be free flight forced (under weight = 0) ";
      break;
    default:
      break;
    }
  G4cout << G4endl;
}
