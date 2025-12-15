/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVSource.h"
#include "G4PhysicalVolumeStore.hh"
#include "G4RandomTools.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersGeometry.h"

GateVSource::GateVSource() {
  fName = "";
  fStartTime = 0;
  fEndTime = 0;
  fAttachedToVolumeName = "";
  fLocalTranslation = G4ThreeVector();
  fLocalRotation = G4RotationMatrix();
  fMaxN = 0;
  fActivity = 0;
  fHalfLife = -1;
  fDecayConstant = -1;
  fInitialActivity = 0;
}

GateVSource::~GateVSource() = default;

GateVSource::threadLocalT &GateVSource::GetThreadLocalData() {
  return fThreadLocalData.Get();
}

void GateVSource::InitializeUserInfo(py::dict &user_info) {
  // get info from the dict
  fName = DictGetStr(user_info, "name");
  fStartTime = DictGetDouble(user_info, "start_time");
  fEndTime = DictGetDouble(user_info, "end_time");
  fAttachedToVolumeName = DictGetStr(user_info, "attached_to");

  // get user info about activity or nb of events
  fVectorOfMaxN = DictGetVecInt(user_info, "n");
  fMaxN = fVectorOfMaxN[0];
  // fMaxN= DictGetInt(user_info, "n");
  fActivity = DictGetDouble(user_info, "activity");
  fInitialActivity = fActivity;

  // half life ?
  fHalfLife = DictGetDouble(user_info, "half_life");
  fDecayConstant = log(2) / fHalfLife;
}

void GateVSource::UpdateActivity(double time) {
  if (fHalfLife <= 0)
    return;
  fActivity = fInitialActivity * exp(-fDecayConstant * (time - fStartTime));
}

double GateVSource::CalcNextTime(double current_simulation_time) {
  double next_time = current_simulation_time;
  if ((fMaxN <= 0)) {
    next_time =
        current_simulation_time - log(G4UniformRand()) * (1.0 / fActivity);
  }
  return next_time;
}

void GateVSource::PrepareNextRun() {
  auto &l = GetThreadLocalData();
  l.fNumberOfGeneratedEvents = 0;
  fMaxN = fVectorOfMaxN[l.fRunID];
  l.fRunID++;
  SetOrientationAccordingToAttachedVolume();
}

double GateVSource::PrepareNextTime(double current_simulation_time,
                                    double numberOfGeneratedEvents) {
  UpdateActivity(current_simulation_time);
  if ((fMaxN <= 0) || ((fMaxN > numberOfGeneratedEvents) && (fMaxN > 0))) {
    if (current_simulation_time < fStartTime)
      return fStartTime;
    if (current_simulation_time >= fEndTime)
      return -1;

    double next_time = CalcNextTime(current_simulation_time);
    if (next_time >= fEndTime)
      return -1;
    return next_time;
  } else {
    return -1;
  }
  return fStartTime; // FIXME timing ?
}

void GateVSource::GeneratePrimaries(G4Event * /*event*/, double /*time*/) {
  Fatal("GeneratePrimaries must be overloaded");
}

void GateVSource::SetOrientationAccordingToAttachedVolume() {
  auto &l = GetThreadLocalData();
  l.fGlobalRotation = fLocalRotation;
  l.fGlobalTranslation = fLocalTranslation;

  // No change in the translation rotation if mother is the world
  if (fAttachedToVolumeName == "world")
    return;

  // compute global translation rotation and keep it.
  // Will be used, for example, in GenericSource to change position
  ComputeTransformationFromVolumeToWorld(
      fAttachedToVolumeName, l.fGlobalTranslation, l.fGlobalRotation, false);
}

unsigned long
GateVSource::GetExpectedNumberOfEvents(const TimeIntervals &time_intervals) {
  // A MODIF
  if (fMaxN != 0)
    return fMaxN;
  unsigned long n = 0;
  for (auto time_interval : time_intervals)
    n += GetExpectedNumberOfEvents(time_interval);
  return n;
}

unsigned long
GateVSource::GetExpectedNumberOfEvents(const TimeInterval &time_interval) {
  long n = 0;
  const auto t0 = time_interval.first / CLHEP::s;
  const auto t1 = time_interval.second / CLHEP::s;
  const auto a = fInitialActivity / CLHEP::Bq;
  const auto l = fDecayConstant;
  const auto duration = t1 - t0;
  if (fHalfLife <= 0)
    n = (long)round((duration)*a);
  else {
    n = (long)round((fInitialActivity / l) * (exp(-l * time_interval.first) -
                                              exp(-l * time_interval.second)));
  }
  return n;
}
