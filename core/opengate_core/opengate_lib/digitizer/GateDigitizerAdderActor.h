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
#include <cstdint> // Required for uint64_t
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Create a collection of "singles":
 *
 * - when every event ends, we consider all digi in the bottom most volume
 * - sum all deposited energy
 * - compute one single position, either the one the digi with the max energy
 * (EnergyWinnerPosition) or the energy weighted position
 * (EnergyWeightedCentroidPosition)
 *
 * Warning: if the volume is composed of several sub volumes, digi will be
 * grouped independently for all sub-volumes. This is determined thanks to the
 * UniqueVolumeID.
 *
 * Warning: digi will also be grouped according to their weights (for VRT
 * methods)
 *
 * Warning: digi are gathered per Event, not per time.
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

  void InitializeUserInfo(py::dict &user_info) override;

  // Called when the simulation starts (master thread only)
  void StartSimulationAction() override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  void SetGroupVolumeDepth(int depth);

protected:
  // A compact key for grouping hits.
  // It combines the volume ID (as a hash of the depth-specific string)
  // and the weight (as its bit representation) for exact matching.
  struct DigiKey {
    uint64_t volumeID;
    uint64_t weightBits;

    bool operator<(const DigiKey &other) const {
      if (volumeID != other.volumeID) {
        return volumeID < other.volumeID;
      }
      return weightBits < other.weightBits;
    }
  };

  int fGroupVolumeDepth;
  AdderPolicy fPolicy;
  bool fTimeDifferenceFlag;
  bool fNumberOfHitsFlag;
  bool fWeightsAreUsedFlag;

  GateVDigiAttribute *fOutputEdepAttribute{};
  GateVDigiAttribute *fOutputPosAttribute{};
  GateVDigiAttribute *fOutputGlobalTimeAttribute{};
  GateVDigiAttribute *fOutputTimeDifferenceAttribute{};
  GateVDigiAttribute *fOutputNumberOfHitsAttribute{};

  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  void AddDigiPerVolume() const;

  // During computation (thread local)
  struct threadLocalT {
    std::map<DigiKey, GateDigiAdderInVolume *> fMapOfDigiInVolume;

    double *edep;
    G4ThreeVector *pos;
    GateUniqueVolumeID::Pointer *volID;
    double *time;
    double *weight;
    int64_t *track_info_id;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDigitizerAdderActor_h
