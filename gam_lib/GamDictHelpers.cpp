/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHelpers.h"
#include "GamDictHelpers.h"


void check_key(py::dict &user_info, const std::string &key) {
    if (user_info.contains(key.c_str())) return;
    std::string c = "";
    for (auto x:user_info)
        c = c + std::string(py::str(x.first)) + " ";
    Fatal("Cannot find the key '" + key + "' in the list of keys: " + c);
}

G4ThreeVector dict_vec(py::dict &user_info, const std::string &key) {
    check_key(user_info, key);
    auto x = py::list(user_info[key.c_str()]);
    return G4ThreeVector(py::float_(x[0]), py::float_(x[1]), py::float_(x[2]));
}

py::array_t<double> dict_matrix(py::dict &user_info, const std::string &key) {
    check_key(user_info, key);
    auto m = py::array_t<double>(user_info[key.c_str()]);
    return m;
}

double dict_float(py::dict &user_info, const std::string &key) {
    check_key(user_info, key);
    return py::float_(user_info[key.c_str()]);
}

int dict_int(py::dict &user_info, const std::string &key) {
    check_key(user_info, key);
    return py::int_(user_info[key.c_str()]);
}

G4String dict_str(py::dict &user_info, const std::string &key) {
    check_key(user_info, key);
    return G4String(py::str(user_info[key.c_str()]));
}

bool is_in(std::string s, std::vector<std::string> &v) {
    for (auto x:v)
        if (x == s) return true;
    return false;
}

void check_is_in(std::string s, std::vector<std::string> &v) {
    if (is_in(s, v)) return;
    std::string c = "";
    for (auto x:v)
        c = c + x + " ";
    Fatal("Cannot find the value '" + s + "' in the list of possible values: " + c);
}