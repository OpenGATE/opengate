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

/** Score weighted AMDM raw sums on a shared spatial grid with a separate bin axis. */
class GateAMDMActor : public GateVActor {
public:
  using ImageType = itk::Image<double, 3>;
  using ImageType4D = itk::Image<double, 4>;
  /** Construct an MT-capable actor from the current Python user-info dictionary. */
  explicit GateAMDMActor(py::dict &user_info);
  /** Read voxel settings and validate/load the charge-energy LUT before scoring. */
  void InitializeUserInfo(py::dict &user_info) override;
  /** Initialize the base actor and create the 3D/4D ITK image holders. */
  void InitializeCpp() override;
  /** Reset the event count and attach fresh buffers to the current volume pose. */
  void BeginOfRunActionMasterThread(int run_id) override;
  /** Count an event under the same actor-owned lock used for worker scoring. */
  void BeginOfEventAction(const G4Event *) override;
  /** Accumulate a step's weighted MeV, delta*MeV and gamma*delta*MeV raw sums. */
  void SteppingAction(G4Step *) override;
  /** Return the physical-volume name used for run-time geometry attachment. */
  std::string GetPhysicalVolumeName() const { return fPhysicalVolumeName; }
  /** Select the resolved physical volume, including an inherited copy index. */
  void SetPhysicalVolumeName(std::string name) { fPhysicalVolumeName = name; }
  /** Return gamma bins then delta bins for charge and energy in MeV/n.
   * Missing charges and NaN energies return an empty vector; endpoints clamp.
   */
  std::vector<double> Lookup(int charge, double energy) const;

  ImageType::Pointer cpp_amdm_restricted_edep_image;
  ImageType4D::Pointer
      cpp_amdm_delta_image; // raw sums, never normalized in place
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
