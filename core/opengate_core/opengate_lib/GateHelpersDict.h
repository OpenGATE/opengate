/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGATEHELPERSDICT_H
#define OPENGATE_CORE_OPENGATEHELPERSDICT_H

#include <G4RotationMatrix.hh>
#include <G4ThreeVector.hh>
#include <iostream>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

namespace py = pybind11;

void DictCheckKey(py::dict &user_info, const std::string &key);

void CheckIsIn(const std::string &s, std::vector<std::string> &v);

G4ThreeVector DictGetG4ThreeVector(py::dict &user_info, const std::string &key);

py::array_t<double> DictGetMatrix(py::dict &user_info, const std::string &key);

G4RotationMatrix ConvertToG4RotationMatrix(py::array_t<double> &rotation);

G4RotationMatrix DictGetG4RotationMatrix(py::dict &user_info,
                                         const std::string &key);

int DictGetInt(py::dict &user_info, const std::string &key);

bool DictGetBool(py::dict &user_info, const std::string &key);

double DictGetDouble(py::dict &user_info, const std::string &key);

std::string DictGetStr(py::dict &user_info, const std::string &key);

std::vector<std::string> DictGetVecStr(py::dict &user_info,
                                       const std::string &key);

std::vector<double> DictGetVecDouble(py::dict &user_info,
                                     const std::string &key);

std::vector<int> DictGetVecInt(py::dict &user_info, const std::string &key);

std::vector<py::dict> DictGetVecDict(py::dict &user_info,
                                     const std::string &key);

std::vector<std::vector<double>> DictGetVecofVecDouble(py::dict &user_info,
                                                       const std::string &key);

std::vector<G4RotationMatrix>
DictGetVecG4RotationMatrix(py::dict &user_info, const std::string &key);

std::vector<G4ThreeVector> DictGetVecG4ThreeVector(py::dict &user_info,
                                                   const std::string &key);

bool IsIn(const std::string &s, std::vector<std::string> &v);

std::map<std::string, std::string> DictToMap(py::dict &user_info);

bool StrToBool(std::string &s);

double StrToDouble(std::string &s);

G4ThreeVector StrToG4ThreeVector(std::string &s);

#endif // OPENGATE_CORE_OPENGATEHELPERSDICT_H
