/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHelpersDict.h"
#include "GateHelpers.h"

void DictCheckKey(py::dict &user_info, const std::string &key) {
  if (user_info.contains(key.c_str()))
    return;
  std::string c;
  for (auto x : user_info)
    c += std::string(py::str(x.first)) + " ";
  FatalKeyError("Cannot find the key '" + key + "' in the list of keys: " + c);
}

G4ThreeVector DictGetG4ThreeVector(py::dict &user_info,
                                   const std::string &key) {
  DictCheckKey(user_info, key);
  auto x = py::list(user_info[key.c_str()]);
  return {py::float_(x[0]), py::float_(x[1]), py::float_(x[2])};
}

py::array_t<double> DictGetMatrix(py::dict &user_info, const std::string &key) {
  DictCheckKey(user_info, key);
  try {
    auto m = py::array_t<double>(user_info[key.c_str()]);
    return m;
  } catch (std::exception e) {
    Fatal("Expecting a matrix for the key '" + key +
          "' but it fails: " + e.what());
  }
  return {}; // fake, to avoid the warning
}

G4RotationMatrix DictGetG4RotationMatrix(py::dict &user_info,
                                         const std::string &key) {
  auto m = DictGetMatrix(user_info, key);
  return ConvertToG4RotationMatrix(m);
}

G4RotationMatrix ConvertToG4RotationMatrix(py::array_t<double> &rotation) {
  if (rotation.size() != 9) {
    Fatal("Cannot convert the rotation");
  }
  G4ThreeVector colX(*rotation.data(0, 0), *rotation.data(1, 0),
                     *rotation.data(2, 0));
  G4ThreeVector colY(*rotation.data(0, 1), *rotation.data(1, 1),
                     *rotation.data(2, 1));
  G4ThreeVector colZ(*rotation.data(0, 2), *rotation.data(1, 2),
                     *rotation.data(2, 2));
  return G4RotationMatrix(colX, colY, colZ);
}

bool DictGetBool(py::dict &user_info, const std::string &key) {
  DictCheckKey(user_info, key);
  return py::bool_(user_info[key.c_str()]);
}

double DictGetDouble(py::dict &user_info, const std::string &key) {
  DictCheckKey(user_info, key);
  return py::float_(user_info[key.c_str()]);
}

int DictGetInt(py::dict &user_info, const std::string &key) {
  DictCheckKey(user_info, key);
  return py::int_(user_info[key.c_str()]);
}

std::string DictGetStr(py::dict &user_info, const std::string &key) {
  DictCheckKey(user_info, key);
  return py::str(user_info[key.c_str()]);
}

std::vector<std::string> DictGetVecStr(py::dict &user_info,
                                       const std::string &key) {
  DictCheckKey(user_info, key);
  std::vector<std::string> l;
  auto com = py::list(user_info[key.c_str()]);
  for (auto x : com) {
    l.push_back(std::string(py::str(x)));
  }
  return l;
}

std::vector<double> DictGetVecDouble(py::dict &user_info,
                                     const std::string &key) {
  DictCheckKey(user_info, key);
  std::vector<double> l;
  auto com = py::list(user_info[key.c_str()]);
  for (auto x : com) {
    l.push_back(py::float_(py::str(x)));
  }
  return l;
}

std::vector<py::dict> DictGetVecDict(py::dict &user_info,
                                     const std::string &key) {
  DictCheckKey(user_info, key);
  std::vector<py::dict> l;
  auto com = py::list(user_info[key.c_str()]);
  for (auto x : com)
    l.push_back(x.cast<py::dict>());
  return l;
}

std::vector<G4ThreeVector> DictGetVecG4ThreeVector(py::dict &user_info,
                                                   const std::string &key) {
  DictCheckKey(user_info, key);
  std::vector<G4ThreeVector> l;
  auto com = py::list(user_info[key.c_str()]);
  for (auto a : com) {
    auto x = a.cast<py::list>();
    double xx = py::float_(x[0]);
    double yy = py::float_(x[1]);
    double zz = py::float_(x[2]);
    G4ThreeVector v(xx, yy, zz);
    l.push_back(v);
  }
  return l;
}

std::vector<G4RotationMatrix>
DictGetVecG4RotationMatrix(py::dict &user_info, const std::string &key) {
  DictCheckKey(user_info, key);
  std::vector<G4RotationMatrix> l;
  auto com = py::list(user_info[key.c_str()]);
  for (auto a : com) {
    auto ar = a.cast<G4RotationMatrix>();
    l.push_back(ar);
  }
  return l;
}

bool IsIn(const std::string &s, std::vector<std::string> &v) {
  for (const auto &x : v)
    if (x == s)
      return true;
  return false;
}

void CheckIsIn(const std::string &s, std::vector<std::string> &v) {
  if (IsIn(s, v))
    return;
  std::string c;
  for (const auto &x : v)
    c += x + " ";
  Fatal("Cannot find the value '" + s +
        "' in the list of possible values: " + c);
}

std::map<std::string, std::string> DictToMap(py::dict &user_info) {
  std::map<std::string, std::string> map;
  for (auto p : user_info) {
    map[py::str(p.first)] = py::str(p.second);
  }
  return map;
}

bool StrToBool(std::string &s) {
  if (s == "True")
    return true;
  if (s == "False")
    return false;
  DDE(s);
  Fatal("Cannot convert this value to bool");
  return false; // to avoid warning
}

double StrToDouble(std::string &s) { return atof(s.c_str()); }

G4ThreeVector StrToG4ThreeVector(std::string &s) {
  G4ThreeVector n;
  std::replace(s.begin(), s.end(), '[', ' ');
  std::replace(s.begin(), s.end(), ']', ' ');
  std::istringstream f(s);
  std::string v;
  int i = 0;
  while (getline(f, v, ',')) {
    n[i] = atof(v.c_str());
    i += 1;
  }
  return n;
}
