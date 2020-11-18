/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamDictHelpers_h
#define GamDictHelpers_h

#include <iostream>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <G4ThreeVector.hh>

namespace py = pybind11;

void check_key(py::dict &user_info, const std::string &key);

void check_is_in(std::string s, std::vector<std::string> &v);

G4ThreeVector dict_vec(py::dict &user_info, const std::string &key);

py::array_t<double> dict_matrix(py::dict &user_info, const std::string &key);

int dict_int(py::dict &user_info, const std::string &key);

double dict_float(py::dict &user_info, const std::string &key);

G4String dict_str(py::dict &user_info, const std::string &key);

bool is_in(std::string s, std::vector<std::string> &v);

#endif // GamDictHelpers_h
