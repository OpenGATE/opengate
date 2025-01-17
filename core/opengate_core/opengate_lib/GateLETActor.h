/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateLETActor_h
#define GateLETActor_h

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4NistManager.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateWeightedEdepActor.h"
#include "itkImage.h"
#include <pybind11/stl.h>
#include "GateHelpersImage.h"

namespace py = pybind11;

class GateLETActor : public GateWeightedEdepActor {

public:
  // Constructor
  GateLETActor(py::dict &user_info);
  
  //void SteppingAction(G4Step *) override;
  
  double ScoringQuantityFn(G4Step *step, double *secondQuantity) override;

  void InitializeUserInfo(py::dict &user_info) override;
  
//   void AddValuesToImages(G4Step *step,itk::Image<double, 3>::IndexType index) override;

  std::string fAveragingMethod;

};

#endif // GateLETActor_h