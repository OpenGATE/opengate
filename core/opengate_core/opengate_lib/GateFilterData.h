#ifndef OPENGATE_CORE_OPENGATE_LIB_GATEFILTERDATA_H
#define OPENGATE_CORE_OPENGATE_LIB_GATEFILTERDATA_H

#include <G4RunManager.hh>
#include <G4Step.hh>
#include <G4Threading.hh>

#include "GatePrimaryScatterFilter.h"
#include "GateUniqueVolumeIDManager.h"
#include "GateUserEventInformation.h"

namespace attr {

// Energy
struct TotalEnergyDeposit;
struct PostKineticEnergy;
struct PreKineticEnergy;
struct KineticEnergy;
struct TrackVertexKineticEnergy;
struct EventKineticEnergy;

// Time
struct LocalTime;
struct GlobalTime;
struct PreGlobalTime;
struct TimeFromBeginOfEvent;
struct TrackProperTime;

// Misc
struct Weight;
struct TrackID;
struct ParentID;
struct EventID;
struct RunID;
struct ThreadID;
struct TrackCreatorProcess;
struct TrackCreatorModelName;
struct TrackCreatorModelIndex;
struct ProcessDefinedStep;
struct ParticleName;
struct ParentParticleName;
struct ParticleType;
struct TrackVolumeName;
struct TrackVolumeCopyNo;
struct PreStepVolumeCopyNo;
struct PostStepVolumeCopyNo;
struct TrackVolumeInstanceID;
struct PreStepUniqueVolumeID;
struct PostStepUniqueVolumeID;
struct PDGCode;
struct HitUniqueVolumeID;

// Position
struct Position;
struct PostPosition;
struct PrePosition;
struct PrePositionLocal;
struct PostPositionLocal;
struct EventPosition;
struct TrackVertexPosition;

// Direction
struct Direction;
struct PostDirection;
struct PreDirection;
struct PreDirectionLocal;
struct TrackVertexMomentumDirection;
struct EventDirection;

// Polarization
struct Polarization;

// Length
struct StepLength;
struct TrackLength;

// Scatter information
struct UnscatteredPrimaryFlag;

} // namespace attr

template <typename Attr> struct GetAttr;

// Energy
template <> struct GetAttr<attr::TotalEnergyDeposit> {
  static double get(G4Step *step) { return step->GetTotalEnergyDeposit(); }
};

template <> struct GetAttr<attr::PostKineticEnergy> {
  static double get(G4Step *step) {
    return step->GetPostStepPoint()->GetKineticEnergy();
  }
};

template <> struct GetAttr<attr::PreKineticEnergy> {
  static double get(G4Step *step) {
    return step->GetPreStepPoint()->GetKineticEnergy();
  }
};

template <> struct GetAttr<attr::KineticEnergy> {
  static double get(G4Step *step) {
    return step->GetPreStepPoint()->GetKineticEnergy();
  }
};

template <> struct GetAttr<attr::TrackVertexKineticEnergy> {
  static double get(G4Step *step) {
    return step->GetTrack()->GetVertexKineticEnergy();
  }
};

template <> struct GetAttr<attr::EventKineticEnergy> {
  static double get(G4Step *) {
    auto const *event = G4RunManager::GetRunManager()->GetCurrentEvent();
    return event->GetPrimaryVertex(0)->GetPrimary(0)->GetKineticEnergy();
  }
};

// Time
template <> struct GetAttr<attr::LocalTime> {
  static double get(G4Step *step) {
    return step->GetPostStepPoint()->GetLocalTime();
  }
};

template <> struct GetAttr<attr::GlobalTime> {
  static double get(G4Step *step) {
    return step->GetPostStepPoint()->GetGlobalTime();
  }
};

template <> struct GetAttr<attr::PreGlobalTime> {
  static double get(G4Step *step) {
    return step->GetPreStepPoint()->GetGlobalTime();
  }
};

template <> struct GetAttr<attr::TimeFromBeginOfEvent> {
  static double get(G4Step *step) {
    auto const *event = G4RunManager::GetRunManager()->GetCurrentEvent();
    auto const globalTime = step->GetTrack()->GetGlobalTime();
    return globalTime - event->GetPrimaryVertex(0)->GetT0();
  }
};

template <> struct GetAttr<attr::TrackProperTime> {
  static double get(G4Step *step) { return step->GetTrack()->GetProperTime(); }
};

// Misc
template <> struct GetAttr<attr::Weight> {
  static double get(G4Step *step) { return step->GetTrack()->GetWeight(); }
};

template <> struct GetAttr<attr::TrackID> {
  static decltype(auto) get(G4Step *step) {
    return step->GetTrack()->GetTrackID();
  }
};

template <> struct GetAttr<attr::ParentID> {
  static decltype(auto) get(G4Step *step) {
    return step->GetTrack()->GetParentID();
  }
};

template <> struct GetAttr<attr::EventID> {
  static decltype(auto) get(G4Step *) {
    return G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  }
};

template <> struct GetAttr<attr::RunID> {
  static decltype(auto) get(G4Step *) {
    return G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
  }
};

template <> struct GetAttr<attr::ThreadID> {
  static decltype(auto) get(G4Step *) { return G4Threading::G4GetThreadId(); }
};

template <> struct GetAttr<attr::TrackCreatorProcess> {
  static std::string get(G4Step *step) {
    auto const *creatorProcess = step->GetTrack()->GetCreatorProcess();
    if (creatorProcess)
      return creatorProcess->GetProcessName();
    return "none";
  }
};

template <> struct GetAttr<attr::TrackCreatorModelName> {
  static std::string get(G4Step *step) {
    return step->GetTrack()->GetCreatorModelName();
  }
};

template <> struct GetAttr<attr::TrackCreatorModelIndex> {
  static decltype(auto) get(G4Step *step) {
    return step->GetTrack()->GetCreatorModelIndex();
  }
};

template <> struct GetAttr<attr::ProcessDefinedStep> {
  static std::string get(G4Step *step) {
    auto const *p = step->GetPreStepPoint()->GetProcessDefinedStep();
    if (p)
      return p->GetProcessName();
    return "none";
  }
};

template <> struct GetAttr<attr::ParticleName> {
  static std::string get(G4Step *step) {
    return step->GetTrack()->GetParticleDefinition()->GetParticleName();
  }
};

template <> struct GetAttr<attr::ParentParticleName> {
  static std::string get(G4Step *step) {
    auto const *event = G4RunManager::GetRunManager()->GetCurrentEvent();
    auto const *info =
        dynamic_cast<GateUserEventInformation *>(event->GetUserInformation());
    if (info) {
      auto const trackId = step->GetTrack()->GetParentID();
      return info->GetParticleName(trackId);
    }
    return "no_user_event_info";
  }
};

template <> struct GetAttr<attr::ParticleType> {
  static std::string get(G4Step *step) {
    return step->GetTrack()->GetParticleDefinition()->GetParticleType();
  }
};

template <> struct GetAttr<attr::TrackVolumeName> {
  static std::string get(G4Step *step) {
    return step->GetTrack()->GetVolume()->GetName();
  }
};

template <> struct GetAttr<attr::TrackVolumeCopyNo> {
  static decltype(auto) get(G4Step *step) {
    return step->GetTrack()->GetVolume()->GetCopyNo();
  }
};

template <> struct GetAttr<attr::PreStepVolumeCopyNo> {
  static decltype(auto) get(G4Step *step) {
    auto const *touchable = step->GetPreStepPoint()->GetTouchable();
    auto const depth = touchable->GetHistoryDepth();
    return touchable->GetVolume(depth)->GetCopyNo();
  }
};

template <> struct GetAttr<attr::PostStepVolumeCopyNo> {
  static decltype(auto) get(G4Step *step) {
    auto const *touchable = step->GetPostStepPoint()->GetTouchable();
    auto const depth = touchable->GetHistoryDepth();
    return touchable->GetVolume(depth)->GetCopyNo();
  }
};

template <> struct GetAttr<attr::TrackVolumeInstanceID> {
  static decltype(auto) get(G4Step *step) {
    return step->GetTrack()->GetVolume()->GetInstanceID();
  }
};

template <> struct GetAttr<attr::PreStepUniqueVolumeID> {
  static decltype(auto) get(G4Step *step) {
    auto *manager = GateUniqueVolumeIDManager::GetInstance();
    auto const *touchable = step->GetPreStepPoint()->GetTouchable();
    return manager->GetVolumeID(touchable);
  }
};

template <> struct GetAttr<attr::PostStepUniqueVolumeID> {
  static decltype(auto) get(G4Step *step) {
    auto *manager = GateUniqueVolumeIDManager::GetInstance();
    auto const *touchable = step->GetPostStepPoint()->GetTouchable();
    return manager->GetVolumeID(touchable);
  }
};

template <> struct GetAttr<attr::PDGCode> {
  static decltype(auto) get(G4Step *step) {
    return step->GetTrack()->GetParticleDefinition()->GetPDGEncoding();
  }
};

template <> struct GetAttr<attr::HitUniqueVolumeID> {
  static decltype(auto) get(G4Step *step) {
    auto *manager = GateUniqueVolumeIDManager::GetInstance();
    auto const processName =
        step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName();
    if (processName == "Transportation")
      return manager->GetVolumeID(step->GetPreStepPoint()->GetTouchable());
    else
      return manager->GetVolumeID(step->GetPostStepPoint()->GetTouchable());
  }
};

// Position
template <> struct GetAttr<attr::Position> {
  static decltype(auto) get(G4Step *step) {
    auto const pos = step->GetPostStepPoint()->GetPosition();
    return std::vector{pos};
  }
};

template <> struct GetAttr<attr::PostPosition> {
  static decltype(auto) get(G4Step *step) {
    auto const pos = step->GetPostStepPoint()->GetPosition();
    return std::vector{pos};
  }
};

template <> struct GetAttr<attr::PrePosition> {
  static decltype(auto) get(G4Step *step) {
    auto const pos = step->GetPreStepPoint()->GetPosition();
    return std::vector{pos};
  }
};

template <> struct GetAttr<attr::PrePositionLocal> {
  static decltype(auto) get(G4Step *step) {
    auto const *touchable = step->GetPreStepPoint()->GetTouchable();
    auto pos = step->GetPreStepPoint()->GetPosition();
    touchable->GetHistory()->GetTopTransform().ApplyPointTransform(pos);
    return std::vector{pos};
  }
};

template <> struct GetAttr<attr::PostPositionLocal> {
  static decltype(auto) get(G4Step *step) {
    auto const *touchable = step->GetPostStepPoint()->GetTouchable();
    auto pos = step->GetPostStepPoint()->GetPosition();
    touchable->GetHistory()->GetTopTransform().ApplyPointTransform(pos);
    return std::vector{pos};
  }
};

template <> struct GetAttr<attr::EventPosition> {
  static decltype(auto) get(G4Step *) {
    auto const *event = G4RunManager::GetRunManager()->GetCurrentEvent();
    auto const pos = event->GetPrimaryVertex(0)->GetPosition();
    return std::vector{pos};
  }
};

template <> struct GetAttr<attr::TrackVertexPosition> {
  static decltype(auto) get(G4Step *step) {
    auto const pos = step->GetTrack()->GetVertexPosition();
    return std::vector{pos};
  }
};

// Direction
template <> struct GetAttr<attr::Direction> {
  static decltype(auto) get(G4Step *step) {
    auto const dir = step->GetPostStepPoint()->GetMomentumDirection();
    return std::vector{dir};
  }
};

template <> struct GetAttr<attr::PostDirection> {
  static decltype(auto) get(G4Step *step) {
    auto const dir = step->GetPostStepPoint()->GetMomentumDirection();
    return std::vector{dir};
  }
};

template <> struct GetAttr<attr::PreDirection> {
  static decltype(auto) get(G4Step *step) {
    auto const dir = step->GetPreStepPoint()->GetMomentumDirection();
    return std::vector{dir};
  }
};

template <> struct GetAttr<attr::PreDirectionLocal> {
  static decltype(auto) get(G4Step *step) {
    auto const *touchable = step->GetPostStepPoint()->GetTouchable();
    auto dir = step->GetPreStepPoint()->GetMomentumDirection();
    touchable->GetHistory()->GetTopTransform().TransformAxis(dir);
    return std::vector{dir};
  }
};

template <> struct GetAttr<attr::TrackVertexMomentumDirection> {
  static decltype(auto) get(G4Step *step) {
    auto const dir = step->GetTrack()->GetVertexMomentumDirection();
    return std::vector{dir};
  }
};

template <> struct GetAttr<attr::EventDirection> {
  static decltype(auto) get(G4Step *) {
    auto const *event = G4RunManager::GetRunManager()->GetCurrentEvent();
    auto const dir =
        event->GetPrimaryVertex(0)->GetPrimary(0)->GetMomentumDirection();
    return std::vector{dir};
  }
};

// Polarization
template <> struct GetAttr<attr::Polarization> {
  static decltype(auto) get(G4Step *step) {
    auto const pol = step->GetTrack()->GetPolarization();
    return std::vector{pol};
  }
};

// Length
template <> struct GetAttr<attr::StepLength> {
  static double get(G4Step *step) { return step->GetStepLength(); }
};

template <> struct GetAttr<attr::TrackLength> {
  static double get(G4Step *step) { return step->GetTrack()->GetTrackLength(); }
};

// Scatter information
template <> struct GetAttr<attr::UnscatteredPrimaryFlag> {
  static decltype(auto) get(G4Step *step) { return IsUnscatteredPrimary(step); }
};

#endif
