/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSPSVoxelsPosDistribution_h
#define GateSPSVoxelsPosDistribution_h

#include "GateSPSPosDistribution.h"
#include <itkImage.h>

#include <cstddef>
#include <vector>

class GateSPSVoxelsPosDistribution : public GateSPSPosDistribution {

public:
  GateSPSVoxelsPosDistribution();

  ~GateSPSVoxelsPosDistribution() override {}

  // Cannot inherit from GenerateOne
  G4ThreeVector VGenerateOne() override;

  void SetCumulativeDistributionFunction(const double *cdfZ, const double *cdfY,
                                         const double *cdfX, std::size_t nx,
                                         std::size_t ny, std::size_t nz);

  // Image type is 3D float by default (the pixel data are not used
  // nor even allocated. Only useful to convert pixel coordinates
  // to physical coordinates.
  typedef itk::Image<float, 3> ImageType;

  // The image is accessible from the python side
  ImageType::Pointer cpp_image;

  // FIXME : thread local ??
  G4ThreeVector fGlobalTranslation;
  G4RotationMatrix fGlobalRotation;

protected:
  // fCDFX[(z * ny + y) * nx + x]
  // fCDFY[z * ny + y]
  // fCDFZ[z]
  std::vector<double> fCDFX;
  std::vector<double> fCDFY;
  std::vector<double> fCDFZ;
};

#endif // GateSPSVoxelsPosDistribution_h
