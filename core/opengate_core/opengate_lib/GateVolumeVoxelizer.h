/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVolumeVoxelizer_h
#define GateVolumeVoxelizer_h

#include "GateHelpers.h"
#include "itkImage.h"

class GateVolumeVoxelizer {
public:
  GateVolumeVoxelizer();

  typedef itk::Image<unsigned char, 3> ImageType;
  typename ImageType::Pointer fImage;

  void Voxelize();

  std::map<std::string, unsigned char> fLabels;
};

#endif // GateVolumeVoxelizer_h
