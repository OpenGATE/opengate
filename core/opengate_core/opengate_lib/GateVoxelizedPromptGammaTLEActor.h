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
#include <G4VProcess.hh>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

namespace py = pybind11;

class GateVoxelizedPromptGammaTLEActor : public GateVActor {

public:
  // destructor
  ~GateVoxelizedPromptGammaTLEActor() override;

  explicit GateVoxelizedPromptGammaTLEActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void InitializeCpp() override;

  void BeginOfRunActionMasterThread(int run_id);

  int EndOfRunActionMasterThread(int run_id) override;

  void EndOfRunAction(const G4Run *run);

  void BeginOfRunAction(const G4Run *run);

  void BeginOfEventAction(const G4Event *event) override;

  void SteppingAction(G4Step *) override;

  inline bool GetProtonTimeFlag() const { return fProtonTimeFlag; }

  inline void SetProtonTimeFlag(const bool b) { fProtonTimeFlag = b; }

  inline bool GetNeutronTimeFlag() const { return fNeutronTimeFlag; }

  inline void SetNeutronTimeFlag(const bool b) { fNeutronTimeFlag = b; }

  inline bool GetProtonEnergyFlag() const { return fProtonEnergyFlag; }

  inline void SetProtonEnergyFlag(const bool b) { fProtonEnergyFlag = b; }

  inline bool GetNeutronEnergyFlag() const { return fNeutronEnergyFlag; }

  inline void SetNeutronEnergyFlag(const bool b) { fNeutronEnergyFlag = b; }

  void SetVector(py::array_t<double> vect_p, 
                 py::array_t<double> vect_n);

  inline std::string GetPhysicalVolumeName() const {
    return fPhysicalVolumeName;
  }

  // void SetVector(pybind11::array_t<double> vect_p, pybind11::array_t<double>
  // vect_n );

  inline void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }

  std::string fPhysicalVolumeName;

  // Image type
  typedef itk::Image<double, 4> ImageType;
  ImageType::Pointer cpp_tof_neutron_image;
  ImageType::Pointer cpp_tof_proton_image;
  ImageType::Pointer cpp_E_proton_image;
  ImageType::Pointer cpp_E_neutron_image;

  typedef itk::Image<double, 3> Image3DType;
  Image3DType::Pointer volume;

  G4double T0;
  G4int incidentParticles;

  G4int timebins;
  G4double timerange;
  G4int energybins;
  G4double energyrange;

  G4bool fProtonTimeFlag{};
  G4bool fProtonEnergyFlag{};
  G4bool fNeutronTimeFlag{};
  G4bool fNeutronEnergyFlag{};
  G4bool weight;

  G4ThreeVector fsize;
  G4ThreeVector fspacing;
  G4ThreeVector fTranslation;
  std::vector <double> fProtonVector;
  std::vector<double> fNeutronVector;

};

#endif // GateVoxelizedPromptGammaTLEActor_h
