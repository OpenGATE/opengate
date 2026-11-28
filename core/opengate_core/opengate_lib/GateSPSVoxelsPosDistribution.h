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
#include <cstdint>
#include <memory>
#include <vector>

// The alias table (Walker / Vose) of the voxels of an activity image: one
// random number and one table entry per sample, instead of three binary
// searches in the CDFs (slow for large images: cache misses). Only the
// voxels with a non-zero probability are in the table. Read only once
// built: shared by the thread-local sources and by the sources with the
// same image (see VoxelSource on the Python side), to save memory.
struct GateVoxelAliasTable {
  struct Entry {
    float q;             // probability to keep the voxel of this entry
    std::uint32_t self;  // linear index (z * ny + y) * nx + x of the voxel
    std::uint32_t alias; // linear index of the alias voxel
  };
  std::vector<Entry> entries;
  std::size_t nx = 0;
  std::size_t ny = 0;
  std::size_t nz = 0;
};

class GateSPSVoxelsPosDistribution : public GateSPSPosDistribution {

public:
  GateSPSVoxelsPosDistribution();

  ~GateSPSVoxelsPosDistribution() override {}

  // Cannot inherit from GenerateOne
  G4ThreeVector VGenerateOne() override;

  // build a new alias table from the CDFs (the CDFs are not kept)
  void SetCumulativeDistributionFunction(const double *cdfZ, const double *cdfY,
                                         const double *cdfX, std::size_t nx,
                                         std::size_t ny, std::size_t nz);

  // the alias table, to share it with another source (same image)
  std::shared_ptr<GateVoxelAliasTable> GetAliasTable() const { return fTable; }
  void SetAliasTable(std::shared_ptr<GateVoxelAliasTable> table);

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
  std::shared_ptr<GateVoxelAliasTable> fTable;
};

#endif // GateSPSVoxelsPosDistribution_h
