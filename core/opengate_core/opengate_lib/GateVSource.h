/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVSource_h
#define GateVSource_h

#include <G4Cache.hh>
#include <G4Event.hh>
#include <G4RotationMatrix.hh>
#include <pybind11/stl.h>

namespace py = pybind11;

class GateVSource {

public:
  typedef std::pair<double, double> TimeInterval;
  typedef std::vector<TimeInterval> TimeIntervals;

  GateVSource();

  virtual ~GateVSource();

  // May be used to clear some allocated data during a thread
  // (see, for example, GateGenericSource)
  virtual void CleanWorkerThread() {}

  // Called at initialisation to set the source properties from a single dict
  virtual void InitializeUserInfo(py::dict &user_info);

  // Activity at the given time: TAC if set, otherwise the initial activity
  // with the decay (half_life), always multiplied by fActivityScale
  virtual void UpdateActivity(double time);

  // Time Activity Curve (linear interpolation, zero outside the TAC)
  void SetTAC(const std::vector<double> &times,
              const std::vector<double> &activities);

  virtual double CalcNextTime(double current_simulation_time);

  virtual void PrepareNextRun();

  virtual double PrepareNextTime(double current_simulation_time,
                                 unsigned long NumberOfGeneratedEvents);

  virtual void GeneratePrimaries(G4Event *event,
                                 double current_simulation_time);

  virtual void SetOrientationAccordingToAttachedVolume();

  virtual unsigned long
  GetExpectedNumberOfEvents(const TimeIntervals &time_intervals);

  virtual unsigned long
  GetExpectedNumberOfEvents(const TimeInterval &time_interval);

  unsigned long GetRunGeneratedEvents() const { return fRunGeneratedEvents; }
  unsigned long GetTotalGeneratedEvents() const {
    return fTotalGeneratedEvents + fRunGeneratedEvents;
  }

  std::vector<int> GetVectorOfSimulatedEvents() { return fVectorOfMaxN; }

  std::string fName;
  double fStartTime;
  double fEndTime;

  std::string fAttachedToVolumeName;
  std::vector<G4ThreeVector> fTranslations;
  std::vector<G4RotationMatrix> fRotations;

  G4ThreeVector fLocalTranslation;
  G4RotationMatrix fLocalRotation;

  G4ThreeVector fGlobalTranslation;
  G4RotationMatrix fGlobalRotation;
  virtual void Visualize() {}

protected:
  std::vector<int> fVectorOfMaxN;
  unsigned long fMaxN;
  double fActivity;
  double fInitialActivity;
  double fHalfLife;
  double fDecayConstant;

  // Time Activity Curve
  std::vector<double> fTAC_Times;
  std::vector<double> fTAC_Activities;
  double GetTACActivity(double time) const;

  // Scale of the activity (and of the TAC), e.g. the total yield of an energy
  // spectrum whose weights are normalized
  double fActivityScale = 1.0;
  void SetActivityScale(double scale);

  unsigned long fRunGeneratedEvents = 0;
  unsigned long fTotalGeneratedEvents = 0;
  G4int fRunID = 0;
};

#endif // GateVSource_h
