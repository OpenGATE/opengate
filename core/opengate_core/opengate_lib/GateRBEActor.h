/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateRBEActor_h
#define GateRBEActor_h

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

class GateRBEActor : public GateWeightedEdepActor {

public:
  // Constructor
  GateRBEActor(py::dict &user_info);

  virtual void InitializeUserInput(py::dict &user_info) override;
  
  virtual void InitializeCpp() override;
  
  virtual void BeginOfRunActionMasterThread(int run_id) override;
  
  virtual void AddValuesToImages(G4Step *step,itk::Image<double, 3>::IndexType index) override;

  std::string fRBEmodel;
  double fAlpha0;
  double fBeta0;
  double fAreaNucl;
  double fDcut;
  double fSmax;
  ImageType::SizeType size_edep{};
  
  ImageType::Pointer cpp_dose_image;
  // we need an extra image for beta scoring (lemI lda)
  ImageType::Pointer cpp_numerator_beta_image;
  
private:
  std::vector<G4DataVector *> *table;
  
  void CreateLookupTable(py::dict &user_info);
  double GetValue(int Z, float energy);
  size_t FindLowerBound(G4double x, G4DataVector *values) const;


};

#endif // GateRBEActor_h
