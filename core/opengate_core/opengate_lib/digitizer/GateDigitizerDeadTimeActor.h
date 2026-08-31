/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerDeadTimeActor_h
#define GateDigitizerDeadTimeActor_h

#include "GateDigiCollection.h"
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
 * Digitizer module for dead time.
 */

class GateDigitizerDeadTimeActor : public GateVDigitizerWithOutputActor {

public:
  explicit GateDigitizerDeadTimeActor(py::dict &user_info);

  ~GateDigitizerDeadTimeActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void BeginOfRunActionMasterThread(int run_id) override;

  void EndOfEventAction(const G4Event *event) override;

  void EndOfRunAction(const G4Run *run) override;

  void SetGroupVolumeDepth(int depth);

protected:
  enum class DeadTimePolicy {
    NonParalyzable,
    Paralyzable,
  };

  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  // User parameters
  double fDeadTime;
  DeadTimePolicy fPolicy;
  double fSortingTime;
  int fGroupVolumeDepth;

  std::unique_ptr<GateTimeSorter> fTimeSorter;
  std::map<uint64_t, double> fVolumeEndOfDeadTimeInterval;

  // Tracking pointers used by GateTimeSorter output iterator.
  GateUniqueVolumeID::Pointer *fTimeSorterOutputVolID{};
  double *fTimeSorterOutputTime{};

  std::unique_ptr<GateDigiAttributesFiller> fillerOut;

  void ProcessTimeSortedDigis();
};

#endif // GateDigitizerDeadTimeActor_h
