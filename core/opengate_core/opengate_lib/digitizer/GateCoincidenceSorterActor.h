/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateCoincidenceSorterActor_h
#define GateCoincidenceSorterActor_h

#include "GateTimeSorter.h"
#include "GateVDigitizerWithOutputActor.h"
#include <G4Cache.hh>
#include <G4ThreeVector.hh>
#include <pybind11/stl.h>

namespace py = pybind11;

class GateCoincidenceSorterActor : public GateVDigitizerWithOutputActor {

public:
  explicit GateCoincidenceSorterActor(py::dict &user_info);

  ~GateCoincidenceSorterActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void StartSimulationAction() override;

  void EndOfEventAction(const G4Event *event) override;

  void EndOfRunAction(const G4Run *run) override;

  void SetGroupVolumeDepth(int depth);

protected:
  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  enum class MultiplesPolicy {
    RemoveMultiples,
    TakeAllGoods,
    TakeWinnerOfGoods,
    TakeIfOnlyOneGood,
    TakeWinnerIfIsGood,
    TakeWinnerIfAllAreGoods
  };
  enum class TransaxialPlane { XY, YZ, XZ };

  // Coincidence sorter parameters.
  double fWindowSize;
  double fWindowOffset;
  MultiplesPolicy fMultiplesPolicy;
  bool fMultiWindow;
  std::optional<double> fMinTransaxialDistance2{};
  std::optional<double> fMaxAxialDistance{};
  TransaxialPlane fTransaxialPlane{TransaxialPlane::XY};
  int fGroupVolumeDepth;
  double fSortingTime;

  struct TemporaryStorage {
    TemporaryStorage(GateDigiCollection *input, GateDigiCollection *output,
                     const std::string &name_suffix);

    GateDigiCollection *digis;
    GateDigiCollectionIterator iter;
    double *currentTime;
    GateUniqueVolumeID::Pointer *currentVolID;
    G4ThreeVector *currentPos;
    double *currentEdep;

    std::unique_ptr<GateDigiAttributesFiller> fillerIn;
    std::unique_ptr<GateCoincidenceDigiAttributesFiller> fillerOut;
    std::optional<double> earliestTime;
    std::optional<double> latestTime;
  };

  GateTimeSorter fTimeSorter;

  std::unique_ptr<TemporaryStorage> fCurrentStorage;
  std::unique_ptr<TemporaryStorage> fFutureStorage;

  void ProcessTimeSortedSingles();
  void DetectCoincidences(bool lastCall = false);
  bool CoincidenceIsGood(const G4ThreeVector &pos1,
                         const G4ThreeVector &pos2) const;
  std::vector<size_t>
  ApplyPolicy(const std::vector<size_t> &secondSingleIndex,
              const std::vector<double> &secondSingleEdep,
              const std::vector<uint8_t> &goodCoincidence) const;

  struct threadLocalT {
    GateUniqueVolumeID::Pointer *volID;
    double *time;
    G4ThreeVector *pos;
  };

  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateCoincidenceSorterActor_h
