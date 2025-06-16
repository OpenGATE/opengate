/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateARFActor_h
#define GateARFActor_h

#include "GateHelpers.h"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateARFActor : public GateVActor {

public:
  // Callback function
  using ARFFunctionType = std::function<void(GateARFActor *)>;

  // Constructor
  explicit GateARFActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  // Beginning run callback
  void BeginOfRunAction(const G4Run * /*run*/) override;

  // End run callback
  void EndOfRunAction(const G4Run * /*run*/) override;

  int GetCurrentNumberOfHits() const;

  int GetCurrentRunId() const;

  std::vector<double> GetEnergy() const;

  std::vector<double> GetPositionX() const;

  std::vector<double> GetPositionY() const;

  std::vector<double> GetDirectionX() const;

  std::vector<double> GetDirectionY() const;

  std::vector<double> GetDirectionZ() const;

  std::vector<double> GetWeights() const;

  // This main function is called every step in the attached volume
  void SteppingAction(G4Step *) override;

  // set the user "apply" function (python)
  void SetARFFunction(ARFFunctionType &f);

protected:
  int fBatchSize;
  ARFFunctionType fApply;
  bool fKeepNegativeSide;
  std::vector<int> fPlaneAxis;

  // For MT, all threads local variables are gathered here
  struct threadLocalT {
    std::vector<double> fEnergy;
    std::vector<double> fPositionX;
    std::vector<double> fPositionY;
    std::vector<double> fDirectionX;
    std::vector<double> fDirectionY;
    std::vector<double> fDirectionZ;
    std::vector<double> fWeights;
    // number of particles hitting the detector
    int fCurrentNumberOfHits;
    // Current run id (to detect if the run has changed)
    int fCurrentRunId;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateARFActor_h
