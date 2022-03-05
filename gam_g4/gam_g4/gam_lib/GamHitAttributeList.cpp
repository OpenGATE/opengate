/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4Step.hh"
#include "GamHitAttributeManager.h"
#include "G4RunManager.hh"
#include "G4Run.hh"
#include "G4TouchableHistory.hh"

// Macros to reduce the code size
// Use FILLFS when step is not used to avoid warning

#define FILLF [=] (GamVHitAttribute *att, G4Step *step, G4TouchableHistory *)
#define FILLFS [=] (GamVHitAttribute *att, G4Step *, G4TouchableHistory *)

void GamHitAttributeManager::InitializeAllHitAttributes() {

    // -----------------------------------------------------
    // Energy
    DefineHitAttribute("TotalEnergyDeposit", 'D',
                       FILLF { att->FillDValue(step->GetTotalEnergyDeposit()); }
    );
    DefineHitAttribute("KineticEnergy", 'D',
                       FILLF { att->FillDValue(step->GetPostStepPoint()->GetKineticEnergy()); }
    );
    DefineHitAttribute("TrackVertexKineticEnergy", 'D',
                       FILLF { att->FillDValue(step->GetTrack()->GetVertexKineticEnergy()); }
    );

    // -----------------------------------------------------
    // Time
    DefineHitAttribute("LocalTime", 'D',
                       FILLF { att->FillDValue(step->GetPostStepPoint()->GetLocalTime()); }
    );
    DefineHitAttribute("GlobalTime", 'D',
                       FILLF { att->FillDValue(step->GetPostStepPoint()->GetGlobalTime()); }
    );
    DefineHitAttribute("TimeFromBeginOfEvent", 'D',
                       FILLF {
                           auto event = G4RunManager::GetRunManager()->GetCurrentEvent();
                           auto t = step->GetTrack()->GetGlobalTime() - event->GetPrimaryVertex(0)->GetT0();
                           att->FillDValue(t);
                       }
    );

    // -----------------------------------------------------
    // Misc
    DefineHitAttribute("Weight", 'D',
                       FILLF { att->FillDValue(step->GetTrack()->GetWeight()); }
    );
    DefineHitAttribute("TrackID", 'I',
                       FILLF { att->FillIValue(step->GetTrack()->GetTrackID()); }
    );
    DefineHitAttribute("EventID", 'I',
                       FILLFS {
                           auto id = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
                           att->FillIValue(id);
                       }
    );
    DefineHitAttribute("RunID", 'I',
                       FILLFS {
                           auto id = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
                           att->FillIValue(id);
                       }
    );
    DefineHitAttribute("ThreadID", 'I',
                       FILLFS { att->FillIValue(G4Threading::G4GetThreadId()); }
    );
    DefineHitAttribute("TrackCreatorProcess", 'S',
                       FILLF {
                           auto p = step->GetTrack()->GetCreatorProcess();
                           if (p) att->FillSValue(p->GetProcessName());
                           else att->FillSValue("none");
                       }
    );
    DefineHitAttribute("ProcessDefinedStep", 'S',
                       FILLF {
                           auto p = step->GetPostStepPoint()->GetProcessDefinedStep();
                           if (p) att->FillSValue(p->GetProcessName());
                           else att->FillSValue("none");
                       }
    );
    DefineHitAttribute("ParticleName", 'S',
                       FILLF { att->FillSValue(step->GetTrack()->GetParticleDefinition()->GetParticleName()); }
    );
    DefineHitAttribute("TrackVolumeName", 'S',
                       FILLF { att->FillSValue(step->GetTrack()->GetVolume()->GetName()); }
    );
    DefineHitAttribute("TrackVolumeCopyNo", 'I',
                       FILLF { att->FillIValue(step->GetTrack()->GetVolume()->GetCopyNo()); }
    );
    DefineHitAttribute("TrackVolumeInstanceID", 'I',
                       FILLF { att->FillIValue(step->GetTrack()->GetVolume()->GetInstanceID()); }
    );

    // -----------------------------------------------------
    // Position
    // FIXME -> global/local position
    DefineHitAttribute("PostPosition", '3',
                       FILLF { att->Fill3Value(step->GetPostStepPoint()->GetPosition()); }
    );
    DefineHitAttribute("PostDirection", '3',
                       FILLF { att->Fill3Value(step->GetPostStepPoint()->GetMomentumDirection()); }
    );
    DefineHitAttribute("PrePosition", '3',
                       FILLF { att->Fill3Value(step->GetPreStepPoint()->GetPosition()); }
    );
    DefineHitAttribute("PreDirection", '3',
                       FILLF { att->Fill3Value(step->GetPreStepPoint()->GetMomentumDirection()); }
    );
    DefineHitAttribute("EventPosition", '3',
                       FILLFS {
                           auto event = G4RunManager::GetRunManager()->GetCurrentEvent();
                           auto p = event->GetPrimaryVertex(0)->GetPosition();
                           att->Fill3Value(p);
                       }
    );
    DefineHitAttribute("TrackVertexPosition", '3',
                       FILLF { att->Fill3Value(step->GetTrack()->GetVertexPosition()); }
    );
    DefineHitAttribute("TrackVertexMomentumDirection", '3',
                       FILLF { att->Fill3Value(step->GetTrack()->GetVertexMomentumDirection()); }
    );
}
