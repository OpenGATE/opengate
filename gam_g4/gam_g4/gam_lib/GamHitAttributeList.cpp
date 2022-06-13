/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitAttributeManager.h"
#include "GamUniqueVolumeIDManager.h"
#include "G4Step.hh"
#include "G4RunManager.hh"
#include "G4Run.hh"

/* Macros to reduce the code size
   Use FILLFS when step is not used to avoid warning

    In the G4 docs:
    "The second argument of FillHits() method, i.e. G4TouchableHistory, is obsolete and not used.
    If user needs to define an artificial second geometry, use Parallel Geometries."
*/

#define FILLF [=] (GamVHitAttribute *att, G4Step *step)
#define FILLFS [=] (GamVHitAttribute *att, G4Step *)

void GamHitAttributeManager::InitializeAllHitAttributes() {

    // -----------------------------------------------------
    // Energy
    DefineHitAttribute("TotalEnergyDeposit", 'D',
                       FILLF { att->FillDValue(step->GetTotalEnergyDeposit()); }
    );
    DefineHitAttribute("PostKineticEnergy", 'D',
                       FILLF { att->FillDValue(step->GetPostStepPoint()->GetKineticEnergy()); }
    );
    DefineHitAttribute("PreKineticEnergy", 'D',
                       FILLF { att->FillDValue(step->GetPreStepPoint()->GetKineticEnergy()); }
    );
    DefineHitAttribute("KineticEnergy", 'D',
                       // KineticEnergy is the same as PreKineticEnergy
                       FILLF { att->FillDValue(step->GetPreStepPoint()->GetKineticEnergy()); }
    );

    DefineHitAttribute("TrackVertexKineticEnergy", 'D',
                       FILLF { att->FillDValue(step->GetTrack()->GetVertexKineticEnergy()); }
    );

    DefineHitAttribute("EventKineticEnergy", 'D',
                       FILLFS {
                           const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
                           auto e = event->GetPrimaryVertex(0)->GetPrimary(0)->GetKineticEnergy();
                           att->FillDValue(e);
                       }
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
                           /*
                            * GlobalTime = Time since the event in which the track belongs is created
                            *
                            */
                           const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
                           auto t = step->GetTrack()->GetGlobalTime() - event->GetPrimaryVertex(0)->GetT0();
                           att->FillDValue(t);
                       }
    );
    DefineHitAttribute("TrackProperTime", 'D',
                       FILLF {
                           auto t = step->GetTrack()->GetProperTime();
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
                           const auto *p = step->GetTrack()->GetCreatorProcess();
                           if (p != nullptr) att->FillSValue(p->GetProcessName());
                           else att->FillSValue("none");
                       }
    );
    DefineHitAttribute("ProcessDefinedStep", 'S',
                       FILLF {
                           const auto *p = step->GetPreStepPoint()->GetProcessDefinedStep();
                           if (p != nullptr) att->FillSValue(p->GetProcessName());
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
    DefineHitAttribute("PreStepVolumeCopyNo", 'I',
                       FILLF {
                           const auto *touchable = step->GetPreStepPoint()->GetTouchable();
                           auto depth = touchable->GetHistoryDepth();
                           auto copyNb = touchable->GetVolume(depth)->GetCopyNo();
                           att->FillIValue(copyNb);
                       }
    );
    DefineHitAttribute("PostStepVolumeCopyNo", 'I',
                       FILLF {
                           const auto *touchable = step->GetPostStepPoint()->GetTouchable();
                           auto depth = touchable->GetHistoryDepth();
                           auto copyNb = touchable->GetVolume(depth)->GetCopyNo();
                           att->FillIValue(copyNb);
                       }
    );
    DefineHitAttribute("TrackVolumeInstanceID", 'I',
                       FILLF { att->FillIValue(step->GetTrack()->GetVolume()->GetInstanceID()); }
    );
    DefineHitAttribute("PreStepUniqueVolumeID", 'U',
                       FILLF {
                           auto *m = GamUniqueVolumeIDManager::GetInstance();
                           auto uid = m->GetVolumeID(step->GetPreStepPoint()->GetTouchable());
                           att->FillUValue(uid);
                       }
    );
    DefineHitAttribute("PostStepUniqueVolumeID", 'U',
                       FILLF {
                           auto *m = GamUniqueVolumeIDManager::GetInstance();
                           auto uid = m->GetVolumeID(step->GetPostStepPoint()->GetTouchable());
                           att->FillUValue(uid);
                       }
    );
    DefineHitAttribute("HitUniqueVolumeID", 'U',
                       FILLF {
                           /*
                             Like in old GATE (see GateCrystalSD.cc).
                             However, no difference with PostStepUniqueVolumeID.
                             Unsure if needed.
                            */
                           auto *m = GamUniqueVolumeIDManager::GetInstance();
                           if (step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName() ==
                               "Transportation") {
                               auto uid = m->GetVolumeID(step->GetPreStepPoint()->GetTouchable());
                               att->FillUValue(uid);
                           } else {
                               auto uid = m->GetVolumeID(step->GetPostStepPoint()->GetTouchable());
                               att->FillUValue(uid);
                           }
                       }
    );

    // -----------------------------------------------------
    // Position
    // FIXME -> add global/local position
    DefineHitAttribute("Position", '3',
                       // Position is the same as PostPosition
                       FILLF { att->Fill3Value(step->GetPostStepPoint()->GetPosition()); }
    );
    DefineHitAttribute("PostPosition", '3',
                       FILLF { att->Fill3Value(step->GetPostStepPoint()->GetPosition()); }
    );
    DefineHitAttribute("PrePosition", '3',
                       FILLF { att->Fill3Value(step->GetPreStepPoint()->GetPosition()); }
    );
    DefineHitAttribute("EventPosition", '3',
                       FILLFS {
                           const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
                           auto p = event->GetPrimaryVertex(0)->GetPosition();
                           att->Fill3Value(p);
                       }
    );
    DefineHitAttribute("TrackVertexPosition", '3',
                       FILLF { att->Fill3Value(step->GetTrack()->GetVertexPosition()); }
    );
    // -----------------------------------------------------
    // Direction
    DefineHitAttribute("Direction", '3',
                       // Direction is the same as PostDirection
                       FILLF { att->Fill3Value(step->GetPostStepPoint()->GetMomentumDirection()); }
    );
    DefineHitAttribute("PostDirection", '3',
                       FILLF { att->Fill3Value(step->GetPostStepPoint()->GetMomentumDirection()); }
    );
    DefineHitAttribute("PreDirection", '3',
                       FILLF { att->Fill3Value(step->GetPreStepPoint()->GetMomentumDirection()); }
    );
    DefineHitAttribute("TrackVertexMomentumDirection", '3',
                       FILLF { att->Fill3Value(step->GetTrack()->GetVertexMomentumDirection()); }
    );
    DefineHitAttribute("EventDirection", '3',
                       FILLFS {
                           const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
                           auto d = event->GetPrimaryVertex(0)->GetPrimary(0)->GetMomentum();
                           att->Fill3Value(d);
                       }
    );

}
