/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4VPrimitiveScorer.hh"
#include "helpers_itk_image_py.h"

// https://github.com/phcerdan/SGEXT/blob/master/wrap/itk/itk_image_py.cpp

using IUC3P = itk::Image<unsigned char, 3>::Pointer;
using IF3P = itk::Image<float, 3>::Pointer;

void init_itk_image(py::module &m) {
    declare_itk_image_ptr<IUC3P>(m, "IUC3P");
    declare_itk_image_ptr<IF3P>(m, "IF3P");
}