/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerAdderActor_h
#define GateDigitizerAdderActor_h

#include "../GateVActor.h"
#include "G4Cache.hh"
#include "GateDigiCollection.h"
#include "GateDigiCollectionIterator.h"
#include "GateHelpersDigitizer.h"
#include "GateTDigiAttribute.h"
#include "GateVDigitizerWithOutputActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Create a collection of "singles":
 *
 * - when every event ends, we consider all digi in the bottom most volume
 * - sum all deposited energy
 * - compute one single position, either the one the digi with the max energy
 *  (EnergyWinnerPosition) or the energy weighted position
 *  (EnergyWeightedCentroidPosition)
 *
 *  Warning: if the volume is composed of several sub volumes, digi will be
 *  grouped independently for all sub-volumes. This is determined thanks to the
 *  UniqueVolumeID.
 *
 *  Warning: digi are gathered per Event, not per time.
 *
 */

class GateDigiAdderInVolume;

class GateDigitizerAdderActor : public GateVDigitizerWithOutputActor {

public:
  enum AdderPolicy {
    Error,
    EnergyWinnerPosition,
    EnergyWeightedCentroidPosition
  };

  // constructor
  explicit GateDigitizerAdderActor(py::dict &user_info);

  // destructor
  ~GateDigitizerAdderActor() override;

  void InitializeUserInput(py::dict &user_info) override;

  // Called when the simulation start (master thread only)
  void StartSimulationAction() override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  void SetGroupVolumeDepth(int depth);

protected:
  int fGroupVolumeDepth;
  AdderPolicy fPolicy;
  bool fTimeDifferenceFlag;
  bool fNumberOfHitsFlag;

  GateVDigiAttribute *fOutputEdepAttribute{};
  GateVDigiAttribute *fOutputPosAttribute{};
  GateVDigiAttribute *fOutputGlobalTimeAttribute{};
  GateVDigiAttribute *fOutputTimeDifferenceAttribute{};
  GateVDigiAttribute *fOutputNumberOfHitsAttribute{};

  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  void AddDigiPerVolume();

  // During computation (thread local)
  struct threadLocalT {
    // std::map<std::string, std::shared_ptr<GateDigiAdderInVolume>>
    // fMapOfDigiInVolume;
    std::map<std::string, GateDigiAdderInVolume *> fMapOfDigiInVolume;
    double *edep;
    G4ThreeVector *pos;
    GateUniqueVolumeID::Pointer *volID;
    double *time;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDigitizerAdderActor_h
