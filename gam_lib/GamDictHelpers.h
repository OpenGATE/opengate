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

void DictCheckKey(py::dict &user_info, const std::string &key);

void CheckIsIn(std::string s, std::vector<std::string> &v);

G4ThreeVector DictVec(py::dict &user_info, const std::string &key);

py::array_t<double> DictMatrix(py::dict &user_info, const std::string &key);

int DictInt(py::dict &user_info, const std::string &key);

bool DictBool(py::dict &user_info, const std::string &key);

double DictFloat(py::dict &user_info, const std::string &key);

G4String DictStr(py::dict &user_info, const std::string &key);

bool IsIn(std::string s, std::vector<std::string> &v);

#endif // GamDictHelpers_h
