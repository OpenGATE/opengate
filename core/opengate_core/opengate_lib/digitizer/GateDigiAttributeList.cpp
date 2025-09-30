/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "../GatePrimaryScatterFilter.h"
#include "../GateUniqueVolumeIDManager.h"
#include "../GateUserEventInformation.h"
#include "G4Run.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "GateDigiAttributeManager.h"

/* Macros to reduce the code size
   Use FILLFS when the step variable is not used to avoid warning

    In the G4 docs:
    "The second argument of FillHits() method, i.e. G4TouchableHistory, is
   obsolete and not used. If user needs to define an artificial second geometry,
   use Parallel Geometries."
*/

#define FILLF [=](GateVDigiAttribute * att, G4Step * step)
#define FILLFS [=](GateVDigiAttribute * att, G4Step *)

void GateDigiAttributeManager::InitializeAllDigiAttributes() {

  // -----------------------------------------------------
  // Energy
  DefineDigiAttribute(
      "TotalEnergyDeposit", 'D',
      FILLF { att->FillDValue(step->GetTotalEnergyDeposit()); });
  DefineDigiAttribute(
      "PostKineticEnergy", 'D',
      FILLF { att->FillDValue(step->GetPostStepPoint()->GetKineticEnergy()); });
  DefineDigiAttribute(
      "PreKineticEnergy", 'D',
      FILLF { att->FillDValue(step->GetPreStepPoint()->GetKineticEnergy()); });
  DefineDigiAttribute(
      "KineticEnergy", 'D',
      // KineticEnergy is the same as PreKineticEnergy
      FILLF { att->FillDValue(step->GetPreStepPoint()->GetKineticEnergy()); });

  DefineDigiAttribute(
      "TrackVertexKineticEnergy", 'D',
      FILLF { att->FillDValue(step->GetTrack()->GetVertexKineticEnergy()); });

  DefineDigiAttribute(
      "EventKineticEnergy", 'D', FILLFS {
        const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
        auto e = event->GetPrimaryVertex(0)->GetPrimary(0)->GetKineticEnergy();
        att->FillDValue(e);
      });

  // -----------------------------------------------------
  // Time
  DefineDigiAttribute(
      "LocalTime", 'D',
      FILLF { att->FillDValue(step->GetPostStepPoint()->GetLocalTime()); });
  DefineDigiAttribute(
      "GlobalTime", 'D',
      FILLF { att->FillDValue(step->GetPostStepPoint()->GetGlobalTime()); });
  DefineDigiAttribute(
      "PreGlobalTime", 'D',
      FILLF { att->FillDValue(step->GetPreStepPoint()->GetGlobalTime()); });
  DefineDigiAttribute(
      "TimeFromBeginOfEvent", 'D', FILLF {
        /*
         * GlobalTime = Time since the event in which the track belongs is
         * created
         *
         */
        const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
        auto t = step->GetTrack()->GetGlobalTime() -
                 event->GetPrimaryVertex(0)->GetT0();
        att->FillDValue(t);
      });
  DefineDigiAttribute(
      "TrackProperTime", 'D', FILLF {
        auto t = step->GetTrack()->GetProperTime();
        att->FillDValue(t);
      });

  // -----------------------------------------------------
  // Misc
  DefineDigiAttribute(
      "Weight", 'D', FILLF { att->FillDValue(step->GetTrack()->GetWeight()); });
  DefineDigiAttribute(
      "TrackID", 'I',
      FILLF { att->FillIValue(step->GetTrack()->GetTrackID()); });
  DefineDigiAttribute(
      "ParentID", 'I',
      FILLF { att->FillIValue(step->GetTrack()->GetParentID()); });
  DefineDigiAttribute(
      "EventID", 'I', FILLFS {
        auto id =
            G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
        att->FillIValue(id);
      });
  DefineDigiAttribute(
      "RunID", 'I', FILLFS {
        auto id = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
        att->FillIValue(id);
      });
  DefineDigiAttribute(
      "ThreadID", 'I',
      FILLFS { att->FillIValue(G4Threading::G4GetThreadId()); });
  DefineDigiAttribute(
      "TrackCreatorProcess", 'S', FILLF {
        const auto *p = step->GetTrack()->GetCreatorProcess();
        if (p != nullptr)
          att->FillSValue(p->GetProcessName());
        else
          att->FillSValue("none");
      });
  DefineDigiAttribute(
      "TrackCreatorModelName", 'S', FILLF {
        auto name = step->GetTrack()->GetCreatorModelName();
        att->FillSValue(name);
      });
  DefineDigiAttribute(
      "TrackCreatorModelIndex", 'I', FILLF {
        auto i = step->GetTrack()->GetCreatorModelIndex();
        att->FillIValue(i);
      });
  DefineDigiAttribute(
      "ProcessDefinedStep", 'S', FILLF {
        const auto *p = step->GetPostStepPoint()->GetProcessDefinedStep();
        if (p != nullptr)
          att->FillSValue(p->GetProcessName());
        else
          att->FillSValue("none");
      });
  DefineDigiAttribute(
      "ParticleName", 'S', FILLF {
        att->FillSValue(
            step->GetTrack()->GetParticleDefinition()->GetParticleName());
      });
  DefineDigiAttribute(
      "PDGCode", 'I', FILLF {
        att->FillIValue(
            step->GetTrack()->GetParticleDefinition()->GetPDGEncoding());
      });
  DefineDigiAttribute(
      "ParentParticleName", 'S', FILLF {
        const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
        auto track_id = step->GetTrack()->GetParentID();
        auto info = dynamic_cast<GateUserEventInformation *>(
            event->GetUserInformation());
        if (info == nullptr)
          att->FillSValue("no_user_event_info");
        else {
          auto name = info->GetParticleName(track_id);
          att->FillSValue(name);
        }
      });
  DefineDigiAttribute(
      "ParticleType", 'S', FILLF {
        att->FillSValue(
            step->GetTrack()->GetParticleDefinition()->GetParticleType());
      });
  DefineDigiAttribute(
      "TrackVolumeName", 'S',
      FILLF { att->FillSValue(step->GetTrack()->GetVolume()->GetName()); });
  DefineDigiAttribute(
      "TrackVolumeCopyNo", 'I',
      FILLF { att->FillIValue(step->GetTrack()->GetVolume()->GetCopyNo()); });
  DefineDigiAttribute(
      "PreStepVolumeCopyNo", 'I', FILLF {
        const auto *touchable = step->GetPreStepPoint()->GetTouchable();
        const auto depth = touchable->GetHistoryDepth();
        const auto copyNb = touchable->GetVolume(depth)->GetCopyNo();
        att->FillIValue(copyNb);
      });
  DefineDigiAttribute(
      "PostStepVolumeCopyNo", 'I', FILLF {
        const auto *touchable = step->GetPostStepPoint()->GetTouchable();
        const auto depth = touchable->GetHistoryDepth();
        const auto copyNb = touchable->GetVolume(depth)->GetCopyNo();
        att->FillIValue(copyNb);
      });
  DefineDigiAttribute(
      "TrackVolumeInstanceID", 'I', FILLF {
        att->FillIValue(step->GetTrack()->GetVolume()->GetInstanceID());
      });

  // -----------------------------------------------------
  // UniqueVolumeID
  DefineDigiAttribute(
      "PreStepUniqueVolumeID", 'U', FILLF {
        auto *m = GateUniqueVolumeIDManager::GetInstance();
        const auto uid =
            m->GetVolumeID(step->GetPreStepPoint()->GetTouchable());
        att->FillUValue(uid);
      });
  DefineDigiAttribute(
      "PreStepUniqueVolumeIDAsInt", 'I', FILLF {
        auto *m = GateUniqueVolumeIDManager::GetInstance();
        const auto uid =
            m->GetVolumeID(step->GetPreStepPoint()->GetTouchable());
        att->FillIValue(uid->GetNumericID());
      });
  DefineDigiAttribute(
      "PostStepUniqueVolumeID", 'U', FILLF {
        auto *m = GateUniqueVolumeIDManager::GetInstance();
        const auto uid =
            m->GetVolumeID(step->GetPostStepPoint()->GetTouchable());
        att->FillUValue(uid);
      });
  DefineDigiAttribute(
      "PostStepUniqueVolumeIDAsInt", 'I', FILLF {
        auto *m = GateUniqueVolumeIDManager::GetInstance();
        const auto uid =
            m->GetVolumeID(step->GetPostStepPoint()->GetTouchable());
        att->FillIValue(uid->GetNumericID());
      });

  // -----------------------------------------------------
  // Position
  DefineDigiAttribute(
      "Position", '3',
      // Position is the same as PostPosition
      FILLF { att->Fill3Value(step->GetPostStepPoint()->GetPosition()); });
  DefineDigiAttribute(
      "PostPosition", '3',
      FILLF { att->Fill3Value(step->GetPostStepPoint()->GetPosition()); });
  DefineDigiAttribute(
      "PrePosition", '3',
      FILLF { att->Fill3Value(step->GetPreStepPoint()->GetPosition()); });
  DefineDigiAttribute(
      "PrePositionLocal", '3', FILLF {
        const auto *theTouchable = step->GetPreStepPoint()->GetTouchable();
        auto pos = step->GetPreStepPoint()->GetPosition();
        theTouchable->GetHistory()->GetTopTransform().ApplyPointTransform(pos);
        att->Fill3Value(pos);
      });
  DefineDigiAttribute(
      "PostPositionLocal", '3', FILLF {
        const auto *theTouchable = step->GetPostStepPoint()->GetTouchable();
        auto pos = step->GetPostStepPoint()->GetPosition();
        theTouchable->GetHistory()->GetTopTransform().ApplyPointTransform(pos);
        att->Fill3Value(pos);
      });

  DefineDigiAttribute(
      "EventPosition", '3', FILLFS {
        const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
        const auto p = event->GetPrimaryVertex(0)->GetPosition();
        att->Fill3Value(p);
      });
  DefineDigiAttribute(
      "TrackVertexPosition", '3',
      FILLF { att->Fill3Value(step->GetTrack()->GetVertexPosition()); });

  // -----------------------------------------------------
  // Direction
  DefineDigiAttribute(
      "Direction", '3',
      // Direction is the same as PostDirection
      FILLF {
        att->Fill3Value(step->GetPostStepPoint()->GetMomentumDirection());
      });
  DefineDigiAttribute(
      "PostDirection", '3', FILLF {
        att->Fill3Value(step->GetPostStepPoint()->GetMomentumDirection());
      });
  DefineDigiAttribute(
      "PreDirection", '3', FILLF {
        att->Fill3Value(step->GetPreStepPoint()->GetMomentumDirection());
      });
  DefineDigiAttribute(
      "PreDirectionLocal", '3', FILLF {
        const auto *theTouchable = step->GetPreStepPoint()->GetTouchable();
        auto dir = step->GetPreStepPoint()->GetMomentumDirection();
        dir = theTouchable->GetHistory()->GetTopTransform().TransformAxis(dir);
        att->Fill3Value(dir);
      });
  DefineDigiAttribute(
      "TrackVertexMomentumDirection", '3', FILLF {
        att->Fill3Value(step->GetTrack()->GetVertexMomentumDirection());
      });
  DefineDigiAttribute(
      "EventDirection", '3', FILLFS {
        const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
        const auto d =
            event->GetPrimaryVertex(0)->GetPrimary(0)->GetMomentumDirection();
        att->Fill3Value(d);
      });

  // -----------------------------------------------------
  // Polarization
  DefineDigiAttribute(
      "Polarization", '3',
      FILLF { att->Fill3Value(step->GetTrack()->GetPolarization()); });

  // -----------------------------------------------------
  // Length
  DefineDigiAttribute(
      "StepLength", 'D', FILLF { att->FillDValue(step->GetStepLength()); });
  DefineDigiAttribute(
      "CurrentStepNumber", 'I',
      FILLF { att->FillIValue(step->GetTrack()->GetCurrentStepNumber()); });
  DefineDigiAttribute(
      "TrackLength", 'D',
      FILLF { att->FillDValue(step->GetTrack()->GetTrackLength()); });

  // -----------------------------------------------------
  // Scatter information
  DefineDigiAttribute(
      "UnscatteredPrimaryFlag", 'I',
      FILLF { att->FillIValue(IsUnscatteredPrimary(step)); });
}
