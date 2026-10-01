/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   LGPL, see LICENSE.md.
   Original AMDM implementation: Hermann Fuchs, April 2025.
   -------------------------------------------------- */
#ifndef GateAMDMActor_h
#define GateAMDMActor_h

#include "GateAMDMActor_lookUpTable.hh"
#include "GateVActor.h"
#include <G4RotationMatrix.hh>
#include <itkImage.h>
#include <mutex>

class GateAMDMActor : public GateVActor {
public:
  using ImageType = itk::Image<double, 3>;
  using ImageType4D = itk::Image<double, 4>;
  explicit GateAMDMActor(py::dict &user_info);
  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  void BeginOfRunActionMasterThread(int run_id) override;
  void BeginOfEventAction(const G4Event *) override;
  void SteppingAction(G4Step *) override;
  std::string GetPhysicalVolumeName() const { return fPhysicalVolumeName; }
  void SetPhysicalVolumeName(std::string name) { fPhysicalVolumeName = name; }
  std::vector<double> Lookup(int charge, double energy) const;

  ImageType::Pointer cpp_amdm_restricted_edep_image;
  ImageType4D::Pointer cpp_amdm_delta_image; // raw sums, never normalized in place
  ImageType4D::Pointer cpp_amdm_gamma_image;
  int NbOfEvent = 0;

private:
  GateAMDMLookUpTable fTable;
  int fBins = 10;
  std::string fHitType;
  std::string fPhysicalVolumeName;
  G4ThreeVector fTranslation;
  G4RotationMatrix fRotation;
  std::mutex fScoringMutex; // owned by this actor, shared by its workers
};
#endif
