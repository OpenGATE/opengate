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

void CheckIsIn(const std::string &s, std::vector<std::string> &v);

G4ThreeVector Dict3DVector(py::dict &user_info, const std::string &key);

py::array_t<double> DictMatrix(py::dict &user_info, const std::string &key);

G4RotationMatrix ConvertToG4RotationMatrix(py::array_t<double> &rotation);

int DictInt(py::dict &user_info, const std::string &key);

bool DictBool(py::dict &user_info, const std::string &key);

double DictFloat(py::dict &user_info, const std::string &key);

std::string DictStr(py::dict &user_info, const std::string &key);

std::vector<std::string> DictVecStr(py::dict &user_info, const std::string &key);

std::vector<py::dict> DictVecDict(py::dict &user_info, const std::string &key);

std::vector<G4RotationMatrix> DictVecRotation(py::dict &user_info, const std::string &key);

std::vector<G4ThreeVector> DictVec3DVector(py::dict &user_info, const std::string &key);

bool IsIn(const std::string &s, std::vector<std::string> &v);

#endif // GamDictHelpers_h
