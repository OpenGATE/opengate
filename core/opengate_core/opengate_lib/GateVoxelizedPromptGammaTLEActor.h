/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVoxelizedPromptGammaTLEActor_h
#define GateVoxelizedPromptGammaTLEActor_h

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4NistManager.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateDoseActor.h"
#include "GateMaterialMuHandler.h"

#include <pybind11/stl.h>

namespace py = pybind11;

class GateVoxelizedPromptGammaTLEActor : public GateVActor {

public:
  // destructor
  ~GateVoxelizedPromptGammaTLEActor() override;

  explicit GateVoxelizedPromptGammaTLEActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void InitializeCpp() override;

  void BeginOfRunActionMasterThread(int run_id) override;

  int EndOfRunActionMasterThread(int run_id) override;

  void EndOfRunAction(const G4Run *run);

  void BeginOfEventAction(const G4Event *event) override;

  void SteppingAction(G4Step *) override;

  // Image type
  typedef itk::Image<double, 4> ImageType;
  ImageType::Pointer cpp_tof_neutron_image;
  ImageType::Pointer cpp_tof_proton_image;
  ImageType::Pointer cpp_E_proton_image;
  ImageType::Pointer cpp_E_neutron_image;

private:
  G4double T0;
  G4int incidentParticles;
  G4int bins;
  G4double range;
  G4ThreeVector fTranslation;
  G4bool prot;
  G4bool energy;
};

#endif // GateVoxelizedPromptGammaTLEActor_h