/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateImageRegularParameterisation_h
#define GateImageRegularParameterisation_h

#include <G4LogicalVolume.hh>
#include <G4PVParameterised.hh>
#include <G4PhantomParameterisation.hh>
#include <G4VPhysicalVolume.hh>
#include <itkImage.h>

/*
  Voxels of an image volume with the Geant4 "regular" navigation
  (G4PhantomParameterisation + G4RegularNavigation): one parameterised
  volume for all the voxels, in a box container (the image volume). With
  SkipEqualMaterials, the consecutive voxels of the same material are
  crossed in one step (the steps only stop where the material changes).
  The image (labels) and the materials are set as for
  GateImageNestedParameterisation; Construct places the voxels in the
  container.
*/

class GateImageRegularParameterisation : public G4PhantomParameterisation {

public:
  typedef itk::Image<unsigned short, 3> ImageType;
  ImageType::Pointer cpp_image;

  GateImageRegularParameterisation();

  void initialize_image();

  void initialize_material(std::vector<std::string> materials);

  // Place the voxels in the container (the image volume: a box, or a
  // GateImageMaskSolid)
  void Construct(const std::string &name, G4LogicalVolume *containerLV,
                 G4VPhysicalVolume *containerPV, bool skipEqualMaterials);

  // With a regular structure, Geant4 appends G4ScoreSplittingProcess to all
  // the particles (G4RunManagerKernel::CheckRegularGeometry, at each run):
  // it splits the energy of a step among the voxels it crosses, for the
  // sensitive detectors of the voxels. The opengate actors find the voxel
  // themselves and it is very slow: it is deactivated (BeginOfRunAction,
  // each thread) when an image uses the regular navigation.
  static bool fRegularNavigationIsUsed;
  static void DeactivateScoreSplitting();

protected:
  std::vector<G4Material *> fImageMaterials;
  std::vector<std::size_t> fLabels;
  G4LogicalVolume *fVoxelLV = nullptr;
  G4PVParameterised *fVoxelPV = nullptr;
};

#endif // GateImageRegularParameterisation_h
