/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateImageBox_h
#define GateImageBox_h

#include "G4Box.hh"
#include <pybind11/stl.h>

namespace py = pybind11;

// Convert the macro value to a string for displaying
#if USE_VISU > 0
#include "G4Version.hh"
/**
 * Only Geant4 >= 9.6.0 had the G4OpenGLSceneHandler::GetObjectTransformation()
 * method
 */
#if G4VERSION_NUMBER >= 960
#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif /* __APPLE__ */

#define G4VIS_BUILD_OPENGL_DRIVER
#include "private/G4OpenGLSceneHandler.hh"

#define GATEIMAGEBOX_USE_OPENGL 1
#endif /* G4VERSION_NUMBER */
#endif /* DUSE_VISU */

class GateImageBox : public G4Box {
public:
  explicit GateImageBox(py::dict &user_info);
  ~GateImageBox();

  typedef double PixelType;

  void DescribeYourselfTo(G4VGraphicsScene &scene) const;
  void SetSlices(py::dict &user_info);
#ifdef GATEIMAGEBOX_USE_OPENGL
  void InitialiseSlice();
#endif

private:
#ifdef GATEIMAGEBOX_USE_OPENGL
  void DescribeYourselfTo(G4OpenGLSceneHandler &scene) const;

  GLubyte *convertToRGB(std::vector<PixelType> slice) const;
  GLuint genOpenGLTexture(const GLubyte *rgb, int width, int height) const;

  GLuint texture_xy;
  GLuint texture_xz;
  GLuint texture_yz;
#endif
  size_t position_x;
  size_t position_y;
  size_t position_z;
  size_t size_pix_x;
  size_t size_pix_y;
  size_t size_pix_z;
  std::vector<PixelType> sliceXY;
  std::vector<PixelType> sliceXZ;
  std::vector<PixelType> sliceYZ;
};

#endif // GateImageBox_h
