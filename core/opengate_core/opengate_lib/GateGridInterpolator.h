/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateGridInterpolator_h
#define GateGridInterpolator_h

#include <vector>

// Utility class for interpolating field values defined on a regular 3D grid
class GateGridInterpolator {
public:
  // container for grid definition parameters
  class GridDefinition {
  public:
    int nx, ny, nz;    // number of grid points along each axis
    double x0, y0, z0; // origin of the grid in local coordinates
    double dx, dy, dz; // grid spacing along each axis
  };

  // container for field values defined on the grid
  //   must be defined in lexicographical order x->y->z (x slowest, z fastest)
  class FieldValues {
  public:
    std::vector<double> Fx; // Field_x values
    std::vector<double> Fy; // Field_y values
    std::vector<double> Fz; // Field_z values
  };

  // interpolation methods
  enum class InterpolationMethod { Nearest, Trilinear };

  // constructor
  GateGridInterpolator(GridDefinition gridDef, FieldValues fieldValues,
                       InterpolationMethod interpMethod);

  // interpolate the field value at a point given in local coordinates
  void Interpolate(double x, double y, double z, double *field) const;

private:
  GridDefinition m_gridDef;
  FieldValues m_fieldValues;
  InterpolationMethod m_interpMethod;

  // compute the 1D index in the field arrays for given grid indices according
  // to lexicographical order x->y->z (x slowest, z fastest)
  inline int idx(int ix, int iy, int iz) const {
    return ix * (m_gridDef.ny * m_gridDef.nz) + iy * m_gridDef.nz + iz;
  }

  // interpolation methods
  void trilinear(double fx, double fy, double fz, double *field) const;
  void nearest(double fx, double fy, double fz, double *field) const;
};

#endif // GateGridInterpolator_h
