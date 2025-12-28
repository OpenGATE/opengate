/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerPileupActor_h
#define GateDigitizerPileupActor_h

#include "GateTimeSorter.h"
#include "GateVDigitizerWithOutputActor.h"
#include <G4Cache.hh>
#include <G4Navigator.hh>
#include <map>
#include <memory>
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Digitizer module for pile-up.
 */

class GateDigitizerPileupActor : public GateVDigitizerWithOutputActor {

public:
  explicit GateDigitizerPileupActor(py::dict &user_info);

  ~GateDigitizerPileupActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  void SetGroupVolumeDepth(int depth);

protected:
  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  // User parameters
  double fPileupTime;
  int fGroupVolumeDepth;

  // Output attribute pointer
  GateVDigiAttribute *fOutputEdepAttribute{};

  // Struct for storing digis in one particular volume which belong to the same
  // time window.
  struct PileupWindow {
    // Time at which the time window opens.
    double startTime{};
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

  PileupWindow &
  GetPileupWindowForCurrentVolume(GateUniqueVolumeID::Pointer *volume,
                                  std::map<uint64_t, PileupWindow> &windows);

  void ProcessTimeSortedDigis();
  void ProcessPileupWindow(PileupWindow &window);

  struct threadLocalT {
    GateUniqueVolumeID::Pointer *volID;
    double *time;
    double *edep;

    GateTimeSorter fTimeSorter;
    std::map<uint64_t, PileupWindow> fVolumePileupWindows;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDigitizerPileupActor_h
