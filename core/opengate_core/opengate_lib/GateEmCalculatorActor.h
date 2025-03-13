/*!
  \class GateEmCalculatorActor
  \author loic.grevillot@creatis.insa-lyon.fr
          david.sarrut@creatis.insa-lyon.fr
 */

#ifndef GateEmCalculatorActor_h
#define GateEmCalculatorActor_h
#include "G4EmCalculator.hh"
#include "GateVActor.h"
#include <pybind11/stl.h>

//-----------------------------------------------------------------------------
/// \brief Actor displaying stopping powers
namespace py = pybind11;
class GateEmCalculatorActor : public GateVActor {
public:
  // Constructor
  GateEmCalculatorActor(py::dict &user_info);
  ~GateEmCalculatorActor();

  //-----------------------------------------------------------------------------
  /// Saves the data collected to the file
  void CalculateElectronicdEdX();
  // Main function called every step in attached volume
  void SteppingAction(G4Step *);

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run);
  void InitializeUserInfo(py::dict &user_info) override;

  void InitializeCpp() override;

protected:
  const G4ParticleDefinition *GetIonDefinition();

  std::vector<double> mEnergies;
  G4String mPartName;
  G4String mParticleParameters;
  G4String mMaterial;
  G4String mFilename;
  bool mIsGenericIon;

  G4EmCalculator *emcalc;
};

#endif // GateEmCalculatorActor_h
