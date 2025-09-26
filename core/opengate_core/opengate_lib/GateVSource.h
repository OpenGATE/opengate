/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVSource_h
#define GateVSource_h

#include "G4Cache.hh"
#include "G4Event.hh"
#include "G4RotationMatrix.hh"
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

  virtual void UpdateActivity(double time);

  virtual double CalcNextTime(double current_simulation_time);

  virtual void PrepareNextRun();

  virtual double PrepareNextTime(double current_simulation_time,
                                 double NumberOfGeneratedEvents);

  virtual void GeneratePrimaries(G4Event *event,
                                 double current_simulation_time);

  virtual void SetOrientationAccordingToAttachedVolume();

  virtual unsigned long
  GetExpectedNumberOfEvents(const TimeIntervals &time_intervals);

  virtual unsigned long
  GetExpectedNumberOfEvents(const TimeInterval &time_interval);

  G4int GetNumberOfSimulatedEvents() {
    auto &l = fThreadLocalData.Get();
    return l.fNumberOfGeneratedEvents;
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

protected:
  std::vector<int> fVectorOfMaxN;
  unsigned long fMaxN;
  double fActivity;
  double fInitialActivity;
  double fHalfLife;
  double fDecayConstant;

  struct threadLocalT {
    unsigned long fNumberOfGeneratedEvents = 0;
    G4ThreeVector fGlobalTranslation;
    G4RotationMatrix fGlobalRotation;
    G4int fRunID = 0;
  };
  G4Cache<threadLocalT> fThreadLocalData;

  virtual threadLocalT &GetThreadLocalData();
};

#endif // GateVSource_h
