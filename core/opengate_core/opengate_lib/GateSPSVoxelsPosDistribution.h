/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSPSVoxelsPosDistribution_h
#define GateSPSVoxelsPosDistribution_h

#include <utility>

#include "G4ParticleDefinition.hh"
#include "GateSPSPosDistribution.h"
#include "itkImage.h"

class GateSPSVoxelsPosDistribution : public GateSPSPosDistribution {

public:
  GateSPSVoxelsPosDistribution();

  virtual ~GateSPSVoxelsPosDistribution() {}

  // Cannot inherit from GenerateOne
  virtual G4ThreeVector VGenerateOne();

  // DEBUG
  std::vector<int> VGenerateOneDebug();

  // typedef for vector of vector
  typedef std::vector<double> VD;
  typedef std::vector<VD> VD2;
  typedef std::vector<std::vector<VD>> VD3;

  void SetCumulativeDistributionFunction(VD vz, VD2 vy, VD3 vx);

  // Image type is 3D float by default (the pixel data are not used
  // nor even allocated. Only useful to convert pixel coordinates
  // to physical coordinates.
  typedef itk::Image<float, 3> ImageType;

  // The image is accessible from py side
  ImageType::Pointer cpp_image;

  // FIXME : thread local ??
  G4ThreeVector fGlobalTranslation;
  G4RotationMatrix fGlobalRotation;

protected:
  VD3 fCDFX;
  VD2 fCDFY;
  VD fCDFZ;
};

#endif // GateSPSVoxelsPosDistribution_h
