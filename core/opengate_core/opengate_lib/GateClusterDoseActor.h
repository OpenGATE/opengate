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
#include <vector>

namespace py = pybind11;

class GateClusterDoseActor : public GateVActor {

public:
  using Image4DType = itk::Image<double, 4>;
  using Image3DType = itk::Image<double, 3>;

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

  void SetClusterSizes(std::vector<int> clusterSizes) {
    fClusterSizes = std::move(clusterSizes);
  }

  void
  SetClusterDatabaseEnergyGrid(std::vector<std::vector<double>> energyGrid) {
    fClusterDatabaseEnergyGrid = std::move(energyGrid);
  }

  void SetClusterDatabaseCumulativeValues(
      std::vector<std::vector<double>> cumulativeValues) {
    fClusterDatabaseCumulativeValues = std::move(cumulativeValues);
  }

  Image4DType::Pointer cpp_cluster_dose_image;
  Image3DType::Pointer cpp_cluster_volume_image;
  int NbOfEvent = 0;

private:
  double InterpolateCumulativeValue(size_t channelIndex, double energy) const;

  std::string fPhysicalVolumeName;
  G4ThreeVector fTranslation;
  std::string fHitType;
  std::vector<int> fClusterSizes;
  std::vector<std::vector<double>> fClusterDatabaseEnergyGrid;
  std::vector<std::vector<double>> fClusterDatabaseCumulativeValues;
  G4ThreeVector fsize;
  G4ThreeVector fspacing;
};

#endif // GateClusterDoseActor_h
