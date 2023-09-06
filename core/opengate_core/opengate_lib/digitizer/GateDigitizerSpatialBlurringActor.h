/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerGaussianBlurringActor_h
#define GateDigitizerGaussianBlurringActor_h

#include "../GateVActor.h"
#include "GateDigiCollection.h"
#include "GateDigiCollectionIterator.h"
#include "GateHelpersDigitizer.h"
#include "GateTDigiAttribute.h"
#include "GateVDigitizerWithOutputActor.h"
#include <G4Cache.hh>
#include <G4Navigator.hh>
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Digitizer module for blurring a (global) spatial position.
 */

class GateDigitizerSpatialBlurringActor : public GateVDigitizerWithOutputActor {

public:
  // constructor
  explicit GateDigitizerSpatialBlurringActor(py::dict &user_info);

  // destructor
  ~GateDigitizerSpatialBlurringActor() override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

protected:
  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  void BlurCurrentThreeVectorValue();

  std::string fBlurAttributeName;
  G4ThreeVector fBlurSigma3;
  bool fKeepInSolidLimits;
  GateVDigiAttribute *fOutputBlurAttribute{};
  G4AffineTransform fWorldToVolume;
  G4AffineTransform fVolumeToWorld;

  // During computation (thread local)
  struct threadLocalT {
    GateUniqueVolumeID::Pointer *fVolumeId;
    G4ThreeVector *fAtt3Value{};
    G4Navigator *fNavigator = nullptr;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDigitizerGaussianBlurringActor_h
