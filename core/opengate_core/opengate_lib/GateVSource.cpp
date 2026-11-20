/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVSource.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersGeometry.h"
#include <G4RandomTools.hh>
#include <algorithm>
#include <cmath>

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

void GateVSource::InitializeUserInfo(py::dict &user_info) {
  // get info from the dict
  fName = DictGetStr(user_info, "name");
  fStartTime = DictGetDouble(user_info, "start_time");
  fEndTime = DictGetDouble(user_info, "end_time");
  fAttachedToVolumeName = DictGetStr(user_info, "attached_to");

  // get user info about activity or nb of events
  fVectorOfMaxN = DictGetVecInt(user_info, "number_of_primaries");
  fMaxN = fVectorOfMaxN[0];
  // fMaxN = DictGetInt(user_info, "number_of_primaries");
  fActivity = DictGetDouble(user_info, "activity");
  fInitialActivity = fActivity;
  fActivityScale = 1.0; // may be changed by SetActivityScale

  // half life ?
  fHalfLife = DictGetDouble(user_info, "half_life");
  fDecayConstant = log(2) / fHalfLife;
}

void GateVSource::UpdateActivity(double time) {
  if (!fTAC_Times.empty()) {
    fActivity = GetTACActivity(time) * fActivityScale;
    return;
  }
  if (fHalfLife <= 0)
    return;
  fActivity = fInitialActivity * exp(-fDecayConstant * (time - fStartTime));
}

void GateVSource::SetTAC(const std::vector<double> &times,
                         const std::vector<double> &activities) {
  fTAC_Times = times;
  fTAC_Activities = activities;
}

void GateVSource::SetActivityScale(const double scale) {
  // fActivity and fInitialActivity do not include the scale yet
  fActivityScale = scale;
  fActivity *= scale;
  fInitialActivity = fActivity;
}

double GateVSource::GetTACActivity(const double time) const {
  // Below/above the TAC ?
  if (time < fTAC_Times.front() || time > fTAC_Times.back())
    return 0;

  // Search for the time bin
  const auto lower =
      std::lower_bound(fTAC_Times.begin(), fTAC_Times.end(), time);
  auto i = std::distance(fTAC_Times.begin(), lower);

  // Exact match or first sample
  if (i == 0)
    return fTAC_Activities[0];

  // Move to the lower bin edge for the interpolation
  i -= 1;

  // Last element ?
  if (i >= fTAC_Times.size() - 1)
    return fTAC_Activities.back();

  // linear interpolation
  const double bin_time = fTAC_Times[i + 1] - fTAC_Times[i];
  const double w1 = (fTAC_Times[i + 1] - time) / bin_time;
  const double w2 = (time - fTAC_Times[i]) / bin_time;
  return fTAC_Activities[i] * w1 + fTAC_Activities[i + 1] * w2;
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
  fTotalGeneratedEvents += fRunGeneratedEvents;
  fRunGeneratedEvents = 0;
  fMaxN = fVectorOfMaxN[fRunID];
  fRunID++;
  SetOrientationAccordingToAttachedVolume();
}

double GateVSource::PrepareNextTime(double current_simulation_time,
                                    unsigned long numberOfGeneratedEvents) {
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
  fGlobalRotation = fLocalRotation;
  fGlobalTranslation = fLocalTranslation;

  // No change in the translation rotation if mother is the world
  if (fAttachedToVolumeName == "world")
    return;

  // compute global translation rotation and keep it.
  // Will be used, for example, in GenericSource to change position
  ComputeTransformationFromVolumeToWorld(
      fAttachedToVolumeName, fGlobalTranslation, fGlobalRotation, false);
}

unsigned long
GateVSource::GetExpectedNumberOfEvents(const TimeIntervals &time_intervals) {
  if (!fVectorOfMaxN.empty()) {
    unsigned long total = 0;
    for (size_t i = 0; i < time_intervals.size() && i < fVectorOfMaxN.size();
         ++i) {
      total += fVectorOfMaxN[i];
    }
    if (total > 0)
      return total;
  }
  unsigned long n = 0;
  for (auto time_interval : time_intervals)
    n += GetExpectedNumberOfEvents(time_interval);
  return n;
}

unsigned long
GateVSource::GetExpectedNumberOfEvents(const TimeInterval &time_interval) {
  // Only the part of the interval during which the source is active
  const auto t0 = std::max(time_interval.first, fStartTime);
  const auto t1 = std::min(time_interval.second, fEndTime);
  if (t1 <= t0)
    return 0;
  // Integral of the activity (Geant4 units: activity x time = number)
  double n = 0;
  if (!fTAC_Times.empty()) {
    // Integral of the linearly interpolated TAC (trapezoids, exact)
    for (size_t i = 0; i + 1 < fTAC_Times.size(); i++) {
      const auto a = std::max(t0, fTAC_Times[i]);
      const auto b = std::min(t1, fTAC_Times[i + 1]);
      if (b <= a)
        continue;
      n += (b - a) * (GetTACActivity(a) + GetTACActivity(b)) / 2.0;
    }
    n *= fActivityScale;
  } else if (fHalfLife <= 0)
    n = fInitialActivity * (t1 - t0);
  else {
    // the decay starts at fStartTime, like in UpdateActivity
    const auto l = fDecayConstant;
    n = (fInitialActivity / l) *
        (exp(-l * (t0 - fStartTime)) - exp(-l * (t1 - fStartTime)));
  }
  return (unsigned long)std::round(n);
}
