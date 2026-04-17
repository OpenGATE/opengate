/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateClusterDoseActor_h
#define GateClusterDoseActor_h

#include "GateVActor.h"
#include "itkImage.h"

namespace py = pybind11;

class GateClusterDoseActor : public GateVActor {

public:
  explicit GateClusterDoseActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void InitializeCpp() override;

  void SteppingAction(G4Step *) override;

  void BeginOfEventAction(const G4Event *event) override;

  void BeginOfRunActionMasterThread(int run_id) override;

  std::string GetPhysicalVolumeName() const { return fPhysicalVolumeName; }

  void SetPhysicalVolumeName(std::string s) {
    fPhysicalVolumeName = std::move(s);
  }

  using Image3DType = itk::Image<double, 3>;

  Image3DType::Pointer cpp_cluster_dose_image;
  int NbOfEvent = 0;

private:
  std::string fPhysicalVolumeName;
  G4ThreeVector fTranslation;
  std::string fHitType;
  int fClusterSize = 0;
  std::string fClusterSizeDatabase;
};

#endif // GateClusterDoseActor_h
