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

  void SetClusterDatabaseEnergyGrid(std::vector<double> energyGrid) {
    fClusterDatabaseEnergyGrid = std::move(energyGrid);
  }

  void SetClusterDatabaseValues(std::vector<double> values) {
    fClusterDatabaseValues = std::move(values);
  }

  Image3DType::Pointer cpp_numerator_image;
  Image3DType::Pointer cpp_denominator_image;
  int NbOfEvent = 0;

private:
  double InterpolateDatabaseValue(double energy) const;

  std::string fPhysicalVolumeName;
  G4ThreeVector fTranslation;
  std::string fHitType;
  std::string fIonizationParameter;
  std::vector<double> fClusterDatabaseEnergyGrid;
  std::vector<double> fClusterDatabaseValues;
};

#endif // GateClusterDoseActor_h
