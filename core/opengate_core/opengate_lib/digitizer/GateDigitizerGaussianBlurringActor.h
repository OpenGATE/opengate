/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerGaussianBlurringActor_h
#define GateDigitizerGaussianBlurringActor_h

#include "../GateVActor.h"
#include "G4Cache.hh"
#include "GateDigiCollection.h"
#include "GateDigiCollectionIterator.h"
#include "GateHelpersDigitizer.h"
#include "GateTDigiAttribute.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * TODO
 */

class GateDigitizerGaussianBlurringActor : public GateVActor {

public:
  explicit GateDigitizerGaussianBlurringActor(py::dict &user_info);

  ~GateDigitizerGaussianBlurringActor() override;

  // Called when the simulation start (master thread only)
  void StartSimulationAction() override;

  // Called when the simulation end (master thread only)
  void EndSimulationAction() override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event starts
  void BeginOfEventAction(const G4Event *event) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  void EndOfSimulationWorkerAction(const G4Run * /*unused*/) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  void SetGroupVolumeDepth(int depth);

protected:
  std::string fOutputFilename;
  std::string fInputDigiCollectionName;
  std::string fOutputDigiCollectionName;
  GateDigiCollection *fOutputDigiCollection;
  GateDigiCollection *fInputDigiCollection;
  std::vector<std::string> fUserSkipDigiAttributeNames;
  int fClearEveryNEvents;

  void InitializeComputation();

  std::string fBlurAttributeName;
  double fBlurSigma;
  double fBlurFWHM;
  std::string fBlurMethod;
  double fBlurReferenceValue;
  double fBlurResolution;
  double fBlurSlope;

  // This member store the function use to blur (Gaussien, InverseSquare etc)
  std::function<double(double)> fBlurValue;
  double GaussianBlur(double value);
  double InverseSquare(double value);
  double Linear(double value);

  GateVDigiAttribute *fOutputBlurAttribute{};

  // During computation (thread local)
  struct threadLocalT {
    GateDigiAttributesFiller *fDigiAttributeFiller;
    GateDigiCollection::Iterator fInputIter;
    double *fAttValue;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDigitizerGaussianBlurringActor_h
