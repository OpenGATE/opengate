/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHelpers.h"
#include "GamDictHelpers.h"


void DictCheckKey(py::dict &user_info, const std::string &key) {
    if (user_info.contains(key.c_str())) return;
    std::string c = "";
    for (auto x:user_info)
        c = c + std::string(py::str(x.first)) + " ";
    Fatal("Cannot find the key '" + key + "' in the list of keys: " + c);
}

G4ThreeVector DictVec(py::dict &user_info, const std::string &key) {
    DictCheckKey(user_info, key);
    auto x = py::list(user_info[key.c_str()]);
    return G4ThreeVector(py::float_(x[0]), py::float_(x[1]), py::float_(x[2]));
}

py::array_t<double> DictMatrix(py::dict &user_info, const std::string &key) {
    DictCheckKey(user_info, key);
    auto m = py::array_t<double>(user_info[key.c_str()]);
    return m;
}

double DictFloat(py::dict &user_info, const std::string &key) {
    DictCheckKey(user_info, key);
    return py::float_(user_info[key.c_str()]);
}

int DictInt(py::dict &user_info, const std::string &key) {
    DictCheckKey(user_info, key);
    return py::int_(user_info[key.c_str()]);
}

G4String DictStr(py::dict &user_info, const std::string &key) {
    DictCheckKey(user_info, key);
    return G4String(py::str(user_info[key.c_str()]));
}

bool IsIn(std::string s, std::vector<std::string> &v) {
    for (auto x:v)
        if (x == s) return true;
    return false;
}

void CheckIsIn(std::string s, std::vector<std::string> &v) {
    if (IsIn(s, v)) return;
    std::string c = "";
    for (auto x:v)
        c = c + x + " ";
    Fatal("Cannot find the value '" + s + "' in the list of possible values: " + c);
}