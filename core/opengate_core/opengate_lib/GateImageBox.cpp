/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateImageBox.h"

#include "G4Polyhedron.hh"
#include "G4VGraphicsScene.hh"
#include "G4VisManager.hh"
#include "GateHelpersDict.h"

#include <typeinfo>

//-----------------------------------------------------------------------------
GateImageBox::GateImageBox(py::dict &user_info)
    : G4Box(DictGetStr(user_info, "name"),
            DictGetVecDouble(user_info, "half_size_mm")[0],
            DictGetVecDouble(user_info, "half_size_mm")[1],
            DictGetVecDouble(user_info, "half_size_mm")[2]) {
  size_pix_x = DictGetVecInt(user_info, "size")[0];
  size_pix_y = DictGetVecInt(user_info, "size")[1];
  size_pix_z = DictGetVecInt(user_info, "size")[2];
  position_x = std::round(size_pix_x * 0.5);
  position_y = std::round(size_pix_y * 0.5);
  position_z = std::round(size_pix_z * 0.5);
}
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
GateImageBox::~GateImageBox() {}
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
void GateImageBox::SetSlices(py::dict &user_info) {
  sliceXY = DictGetVecDouble(user_info, "slice_xy");
  sliceXZ = DictGetVecDouble(user_info, "slice_xz");
  sliceYZ = DictGetVecDouble(user_info, "slice_yz");
}
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
void GateImageBox::DescribeYourselfTo(G4VGraphicsScene &scene) const {
#ifdef GATEIMAGEBOX_USE_OPENGL
  try {
    G4OpenGLSceneHandler &opengl = dynamic_cast<G4OpenGLSceneHandler &>(scene);
    scene.AddSolid(*this);
    DescribeYourselfTo(opengl);
  } catch (std::bad_cast exp) {
    scene.AddSolid(*this);
  }
#else
  scene.AddSolid(*this);
#endif
}
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
#ifdef GATEIMAGEBOX_USE_OPENGL
void GateImageBox::DescribeYourselfTo(G4OpenGLSceneHandler &scene) const {

  scene.BeginPrimitives(scene.GetObjectTransformation());

  GLfloat xHalfLength = GetXHalfLength();
  GLfloat yHalfLength = GetYHalfLength();
  GLfloat zHalfLength = GetZHalfLength();

  GLfloat x = position_x * xHalfLength * 2 / size_pix_x - xHalfLength;
  GLfloat y = position_y * yHalfLength * 2 / size_pix_y - yHalfLength;
  GLfloat z = position_z * zHalfLength * 2 / size_pix_z - zHalfLength;

  glPushAttrib(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
  glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);

  GLfloat *color = new GLfloat[4];
  glGetFloatv(GL_CURRENT_COLOR, color);

  glColor3f(1.f, 1.0f, 1.0f);

  glEnable(GL_TEXTURE_2D);

  glBindTexture(GL_TEXTURE_2D, texture_xy);
  glBegin(GL_QUADS);
  glTexCoord2d(0, 0);
  glVertex3f(-xHalfLength, -yHalfLength, z);
  glTexCoord2d(0, 1);
  glVertex3f(-xHalfLength, yHalfLength, z);
  glTexCoord2d(1, 1);
  glVertex3f(xHalfLength, yHalfLength, z);
  glTexCoord2d(1, 0);
  glVertex3f(xHalfLength, -yHalfLength, z);
  glEnd();

  glBindTexture(GL_TEXTURE_2D, texture_yz);
  glBegin(GL_QUADS);
  glTexCoord2d(0, 0);
  glVertex3f(x, -yHalfLength, -zHalfLength);
  glTexCoord2d(1, 0);
  glVertex3f(x, yHalfLength, -zHalfLength);
  glTexCoord2d(1, 1);
  glVertex3f(x, yHalfLength, zHalfLength);
  glTexCoord2d(0, 1);
  glVertex3f(x, -yHalfLength, zHalfLength);
  glEnd();

  glBindTexture(GL_TEXTURE_2D, texture_xz);
  glBegin(GL_QUADS);
  glTexCoord2d(0, 0);
  glVertex3f(-xHalfLength, y, -zHalfLength);
  glTexCoord2d(0, 1);
  glVertex3f(-xHalfLength, y, zHalfLength);
  glTexCoord2d(1, 1);
  glVertex3f(xHalfLength, y, zHalfLength);
  glTexCoord2d(1, 0);
  glVertex3f(xHalfLength, y, -zHalfLength);
  glEnd();

  glDisable(GL_TEXTURE_2D);

  glColor3f(0.5f, 0.5f, 0.5f);
  glBegin(GL_LINE_LOOP);
  glVertex3f(-xHalfLength, -yHalfLength, z);
  glVertex3f(-xHalfLength, yHalfLength, z);
  glVertex3f(xHalfLength, yHalfLength, z);
  glVertex3f(xHalfLength, -yHalfLength, z);
  glEnd();

  glBegin(GL_LINE_LOOP);
  glVertex3f(x, -yHalfLength, -zHalfLength);
  glVertex3f(x, yHalfLength, -zHalfLength);
  glVertex3f(x, yHalfLength, zHalfLength);
  glVertex3f(x, -yHalfLength, zHalfLength);
  glEnd();

  glBegin(GL_LINE_LOOP);
  glVertex3f(-xHalfLength, y, -zHalfLength);
  glVertex3f(-xHalfLength, y, zHalfLength);
  glVertex3f(xHalfLength, y, zHalfLength);
  glVertex3f(xHalfLength, y, -zHalfLength);
  glEnd();

  glColor3fv(color);
  delete[] color;

  glPopAttrib();

  scene.EndPrimitives();
}
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
GLubyte *GateImageBox::convertToRGB(std::vector<PixelType> slice) const {
  GLubyte *rgb = new GLubyte[slice.size() * 3];

  int i = 0;
  for (std::vector<PixelType>::iterator it = slice.begin(); it != slice.end();
       ++it) {
    PixelType pixel = *it;
    pixel *= std::numeric_limits<GLubyte>::max();

    GLubyte gray = static_cast<GLubyte>(pixel);
    rgb[i] = gray;
    rgb[i + 1] = gray;
    rgb[i + 2] = gray;
    i += 3;
  }
  return rgb;
}
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
GLuint GateImageBox::genOpenGLTexture(const GLubyte *rgb, int width,
                                      int height) const {
  GLuint texture;
  glGenTextures(1, &texture);
  glBindTexture(GL_TEXTURE_2D, texture);
  glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
  glPixelStorei(GL_PACK_ALIGNMENT, 1);
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB,
               GL_UNSIGNED_BYTE, (GLvoid *)rgb);
  glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
  return texture;
}
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// void GateImageBox::InitialiseSlice(std::vector<PixelType> & sliceXY,
// std::vector<PixelType> & sliceXZ, std::vector<PixelType> & sliceYZ, const
// double resol_x, const double resol_y, const double resol_z) {
void GateImageBox::InitialiseSlice() {
  {
    GLubyte *rgb = convertToRGB(sliceXY);
    texture_xy = genOpenGLTexture(rgb, size_pix_x, size_pix_y);
    delete[] rgb;
  }

  {
    GLubyte *rgb = convertToRGB(sliceXZ);
    texture_xz = genOpenGLTexture(rgb, size_pix_x, size_pix_z);
    delete[] rgb;
  }

  {
    GLubyte *rgb = convertToRGB(sliceYZ);
    texture_yz = genOpenGLTexture(rgb, size_pix_y, size_pix_z);
    delete[] rgb;
  }
}
//-----------------------------------------------------------------------------

#endif
