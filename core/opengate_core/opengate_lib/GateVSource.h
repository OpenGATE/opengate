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
  GateVSource();

  virtual ~GateVSource();

  // May be used to clear some allocated data during a thread
  // (see for example GateGenericSource)
  virtual void CleanWorkerThread() {}

  // Called at initialisation to set the source properties from a single dict
  virtual void InitializeUserInfo(py::dict &user_info);

  virtual void PrepareNextRun();

  virtual double PrepareNextTime(double current_simulation_time);

  virtual void GeneratePrimaries(G4Event *event, double time);

  virtual void SetOrientationAccordingToMotherVolume();

  std::string fName;
  double fStartTime;
  double fEndTime;
  std::string fMother;
  std::vector<G4ThreeVector> fTranslations;
  std::vector<G4RotationMatrix> fRotations;

  G4ThreeVector fLocalTranslation;
  G4RotationMatrix fLocalRotation;

  struct threadLocalT {
    G4ThreeVector fGlobalTranslation;
    G4RotationMatrix fGlobalRotation;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateVSource_h
