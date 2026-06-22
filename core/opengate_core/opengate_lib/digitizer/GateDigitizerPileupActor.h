/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerPileupActor_h
#define GateDigitizerPileupActor_h

#include "../GateUniqueVolumeID.h"
#include "GateDigiCollection.h"
#include "GateDigiCollectionIterator.h"
#include "GateTimeSorter.h"
#include "GateVDigitizerWithOutputActor.h"
#include <G4Cache.hh>
#include <G4Navigator.hh>
#include <map>
#include <memory>
#include <pybind11/stl.h>
#include <queue>

namespace py = pybind11;

/*
 * Digitizer module for pile-up.
 */

class GateDigitizerPileupActor : public GateVDigitizerWithOutputActor {

public:
  explicit GateDigitizerPileupActor(py::dict &user_info);

  ~GateDigitizerPileupActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void BeginOfRunActionMasterThread(int run_id) override;

  void EndOfEventAction(const G4Event *event) override;

  void EndOfRunAction(const G4Run *run) override;

  void SetGroupVolumeDepth(int depth);

protected:
  enum class TimeWindowPolicy {
    NonParalyzable,
    Paralyzable,
    EnergyWinnerParalyzable
  };
  enum class PositionAttributePolicy { EnergyWinner, EnergyWeightedCentroid };
  enum class AttributePolicy { First, EnergyWinner, Last };

  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  // User parameters
  double fTimeWindow;
  TimeWindowPolicy fTimeWindowPolicy;
  AttributePolicy fAttributePolicy;
  PositionAttributePolicy fPositionAttributePolicy;
  double fSortingTime;
  int fGroupVolumeDepth;

  // Struct for storing digis in one particular volume which belong to the same
  // time window.
  struct PileupWindow {
    // Hash of the corresponding volume.
    uint64_t hash{};
    // Time at which the time window opens.
    double startTime{};
    // Higehst energy deposit in the window.
    double highestEdep{};
    // Collection of digis in the same time window.
    GateDigiCollection *digis;
    // Iterator used to loop over the digis for simulating pile-up.
    GateDigiCollectionIterator digiIter;
    // Filler used to copy digi attributes from the input collection into the
    // window.
    std::unique_ptr<GateDigiAttributesFiller> fillerIn;
    // Filler used to copy the pile-up digi from the window into the output
    // collection.
    std::unique_ptr<GateDigiAttributesFiller> fillerOut;
  };

  // Struct that represents when a pile-up window expires.
  struct volumeWindowExpiry {
    uint64_t volumeHash;
    double expiryTime;
  };

  std::unique_ptr<GateTimeSorter> fTimeSorter;
  std::map<uint64_t, PileupWindow> fVolumePileupWindows;
  std::queue<volumeWindowExpiry> fWindowExpiry;

  // Tracking pointers used by GateTimeSorter output iterator.
  GateUniqueVolumeID::Pointer *fTimeSorterOutputVolID{};
  double *fTimeSorterOutputTime{};
  double *fTimeSorterOutputEdep{};

  // Tracking pointers used by PileupWindow digi iterator.
  double *fPileupWindowEdep{};
  G4ThreeVector *fPileupWindowPos{};

  PileupWindow &
  GetPileupWindowForCurrentVolume(GateUniqueVolumeID::Pointer *volume,
                                  std::map<uint64_t, PileupWindow> &windows);

  void ProcessTimeSortedDigis();
  void ProcessPileupWindow(PileupWindow &window);
  void ProcessPileupWindows(double currentTime);
};

#endif // GateDigitizerPileupActor_h
