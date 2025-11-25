/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGATEDIGITIZERPROJECTIONACTOR_H
#define OPENGATE_CORE_OPENGATEDIGITIZERPROJECTIONACTOR_H

#include "../GateVActor.h"
#include "G4Cache.hh"
#include "GateDigiCollection.h"
#include "GateHelpersDigitizer.h"
#include "itkImage.h"

/*
 * Actor that creates some projections (2D images) from several Digi Collections
 * in the same volume.
 *
 * WARNING: takes the particle's weight into account only if "Weight" is
 * included in the attribute list.
 */

class GateDigitizerProjectionActor : public GateVActor {

public:
  explicit GateDigitizerProjectionActor(py::dict &user_info);

  ~GateDigitizerProjectionActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void InitializeCpp() override;

  // Called when the simulation starts (master thread only)
  void StartSimulationAction() override;

  // Called every time a Run starts (master thread)
  void BeginOfRunActionMasterThread(int run_id) override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  void SetPhysicalVolumeName(const std::string &name);

  void EnableSquaredImage(bool b);

  // Image type is 3D float by default
  typedef itk::Image<double, 3> ImageType;
  typedef itk::Image<int, 3> ImageIDType;
  ImageType::Pointer fImage;
  ImageType::Pointer fSquaredImage;
  std::string fPhysicalVolumeName;
  bool fSquaredImageIsEnabled;

protected:
  std::vector<std::string> fInputDigiCollectionNames;
  std::vector<GateDigiCollection *> fInputDigiCollections;
  G4RotationMatrix fDetectorOrientationMatrix;

  void ProcessSlice(size_t slice, size_t channel) const;
  void ScoreSquaredValue(const ImageType::IndexType &index,
                         int current_event_id, double value) const;
  void FlushSquaredValues() const;

  G4ThreeVector fPreviousTranslation;
  G4RotationMatrix fPreviousRotation;

  // During computation
  struct threadLocalT {
    std::vector<std::vector<G4ThreeVector> *> fInputPos;
    std::vector<std::vector<double> *> fInputWeights;
    ImageType::Pointer fSquaredTempImage;
    ImageIDType::Pointer fLastEventIdImage;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // OPENGATE_CORE_OPENGATEDIGITIZERPROJECTIONACTOR_H
