/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateBeamQualityActor_h
#define GateBeamQualityActor_h

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4NistManager.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateWeightedEdepActor.h"
#include "itkImage.h"
#include <pybind11/stl.h>
#include "GateHelpersImage.h"

#include "G4DataVector.hh"

namespace py = pybind11;

class GateBeamQualityActor : public GateWeightedEdepActor {

public:
  // Constructor
  GateBeamQualityActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  
  void InitializeCpp() override;
  
  double ScoringQuantityFn(G4Step *step, double *secondQuantity) override;

  std::string fRBEmodel;
  double fAlpha0;
  double fBetaRef;
  double fAreaNucl;
  double fDcut;
  double fSmax;
  int ZMinTable;
  int ZMaxTable;
  Image3DType::SizeType size_edep{};
  
  
private:
  std::vector<G4DataVector *> *table;
  
  void CreateLookupTable(py::dict &user_info);
  double GetValue(int Z, float energy);
  size_t FindLowerBound(G4double x, G4DataVector *values) const;


};

#endif // GateBeamQualityActor_h
