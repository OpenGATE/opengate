/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGridInterpolator.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>

// Constructor: validate that field values have the correct size
GateGridInterpolator::GateGridInterpolator(GridDefinition gridDef,
                                           FieldValues fieldValues,
                                           InterpolationMethod interpMethod)
    : m_gridDef(gridDef), m_fieldValues(std::move(fieldValues)),
      m_interpMethod(interpMethod) {
  // Validate the grid definition and field values
  const int N = gridDef.nx * gridDef.ny * gridDef.nz;
  if ((int)m_fieldValues.Fx.size() != N || (int)m_fieldValues.Fy.size() != N ||
      (int)m_fieldValues.Fz.size() != N) {
    throw std::invalid_argument("GateGridInterpolator: Field value arrays must "
                                "each have nx*ny*nz elements");
  }
}

// interpolate the field value at a point given in local coordinates
void GateGridInterpolator::Interpolate(double x, double y, double z,
                                       double *field) const {
  const auto &g = m_gridDef;
  double fx = (x - g.x0) / g.dx;
  double fy = (y - g.y0) / g.dy;
  double fz = (z - g.z0) / g.dz;

  switch (m_interpMethod) {
  case InterpolationMethod::Nearest:
    nearest(fx, fy, fz, field);
    break;
  case InterpolationMethod::Trilinear:
    trilinear(fx, fy, fz, field);
    break;
  default:
    throw std::runtime_error(
        "GateGridInterpolator: Unknown interpolation method");
  }
}

// Trilinear interpolation
void GateGridInterpolator::trilinear(double fx, double fy, double fz,
                                     double *field) const {
  // Compute the surrounding grid point indices
  const int ix0 = std::clamp((int)std::floor(fx), 0, m_gridDef.nx - 1);
  const int iy0 = std::clamp((int)std::floor(fy), 0, m_gridDef.ny - 1);
  const int iz0 = std::clamp((int)std::floor(fz), 0, m_gridDef.nz - 1);

  const int ix1 = std::clamp(ix0 + 1, 0, m_gridDef.nx - 1);
  const int iy1 = std::clamp(iy0 + 1, 0, m_gridDef.ny - 1);
  const int iz1 = std::clamp(iz0 + 1, 0, m_gridDef.nz - 1);

  // Compute the fractional distances along each axis
  const double tx = std::clamp(fx - ix0, 0.0, 1.0);
  const double ty = std::clamp(fy - iy0, 0.0, 1.0);
  const double tz = std::clamp(fz - iz0, 0.0, 1.0);

  double fieldX =
      m_fieldValues.Fx[idx(ix0, iy0, iz0)] * (1 - tx) * (1 - ty) * (1 - tz) +
      m_fieldValues.Fx[idx(ix1, iy0, iz0)] * tx * (1 - ty) * (1 - tz) +
      m_fieldValues.Fx[idx(ix0, iy1, iz0)] * (1 - tx) * ty * (1 - tz) +
      m_fieldValues.Fx[idx(ix1, iy1, iz0)] * tx * ty * (1 - tz) +
      m_fieldValues.Fx[idx(ix0, iy0, iz1)] * (1 - tx) * (1 - ty) * tz +
      m_fieldValues.Fx[idx(ix1, iy0, iz1)] * tx * (1 - ty) * tz +
      m_fieldValues.Fx[idx(ix0, iy1, iz1)] * (1 - tx) * ty * tz +
      m_fieldValues.Fx[idx(ix1, iy1, iz1)] * tx * ty * tz;

  double fieldY =
      m_fieldValues.Fy[idx(ix0, iy0, iz0)] * (1 - tx) * (1 - ty) * (1 - tz) +
      m_fieldValues.Fy[idx(ix1, iy0, iz0)] * tx * (1 - ty) * (1 - tz) +
      m_fieldValues.Fy[idx(ix0, iy1, iz0)] * (1 - tx) * ty * (1 - tz) +
      m_fieldValues.Fy[idx(ix1, iy1, iz0)] * tx * ty * (1 - tz) +
      m_fieldValues.Fy[idx(ix0, iy0, iz1)] * (1 - tx) * (1 - ty) * tz +
      m_fieldValues.Fy[idx(ix1, iy0, iz1)] * tx * (1 - ty) * tz +
      m_fieldValues.Fy[idx(ix0, iy1, iz1)] * (1 - tx) * ty * tz +
      m_fieldValues.Fy[idx(ix1, iy1, iz1)] * tx * ty * tz;

  double fieldZ =
      m_fieldValues.Fz[idx(ix0, iy0, iz0)] * (1 - tx) * (1 - ty) * (1 - tz) +
      m_fieldValues.Fz[idx(ix1, iy0, iz0)] * tx * (1 - ty) * (1 - tz) +
      m_fieldValues.Fz[idx(ix0, iy1, iz0)] * (1 - tx) * ty * (1 - tz) +
      m_fieldValues.Fz[idx(ix1, iy1, iz0)] * tx * ty * (1 - tz) +
      m_fieldValues.Fz[idx(ix0, iy0, iz1)] * (1 - tx) * (1 - ty) * tz +
      m_fieldValues.Fz[idx(ix1, iy0, iz1)] * tx * (1 - ty) * tz +
      m_fieldValues.Fz[idx(ix0, iy1, iz1)] * (1 - tx) * ty * tz +
      m_fieldValues.Fz[idx(ix1, iy1, iz1)] * tx * ty * tz;

  field[0] = fieldX;
  field[1] = fieldY;
  field[2] = fieldZ;
}

// Nearest-neighbor interpolation
void GateGridInterpolator::nearest(double fx, double fy, double fz,
                                   double *field) const {
  // Compute the nearest grid point indices
  const int ix = std::clamp((int)std::round(fx), 0, m_gridDef.nx - 1);
  const int iy = std::clamp((int)std::round(fy), 0, m_gridDef.ny - 1);
  const int iz = std::clamp((int)std::round(fz), 0, m_gridDef.nz - 1);

  const int i = idx(ix, iy, iz);

  field[0] = m_fieldValues.Fx[i];
  field[1] = m_fieldValues.Fy[i];
  field[2] = m_fieldValues.Fz[i];
}
