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

G4DataVector *VectorToG4DataVector(std::vector<double> data) {
  G4DataVector *vec = new G4DataVector(); // data.size()
  for (int i = 0; i < data.size(); i++) {
    vec->insertAt(i, data[i]);
  }
  return vec;
}

std::vector<std::vector<double>> DictGetVecofVecDouble(py::dict &user_info,
                                                       const std::string &key) {
  DictCheckKey(user_info, key);
  std::vector<std::vector<double>> vec;
  auto com = py::list(user_info[key.c_str()]);

  for (auto x : com) {
    std::vector<double> l;
    for (auto y : x) {
      l.push_back(py::float_(py::str(y)));
    }
    vec.push_back(l);
  }
  return vec;
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

std::vector<int> DictGetVecInt(py::dict &user_info, const std::string &key) {
  DictCheckKey(user_info, key);
  std::vector<int> l;
  auto com = py::list(user_info[key.c_str()]);
  for (auto x : com) {
    l.push_back(py::int_(py::str(x)));
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

std::vector<py::list> DictGetVecList(py::dict &user_info,
                                     const std::string &key) {
  DictCheckKey(user_info, key);
  std::vector<py::list> l;
  auto com = py::list(user_info[key.c_str()]);
  for (auto x : com)
    l.push_back(x.cast<py::list>());
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
    auto m = a.cast<py::array_t<double>>();
    auto ar = ConvertToG4RotationMatrix(m);
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

std::map<std::string, std::string> DictToMap(const py::dict &user_info) {
  std::map<std::string, std::string> map;
  for (auto p : user_info) {
    // copy the strings
    map[std::string(py::str(p.first))] = std::string(py::str(p.second));
  }
  return map;
}

bool StrToBool(const std::string &s) {
  if (s == "True")
    return true;
  if (s == "False")
    return false;
  DDE(s);
  Fatal("Cannot convert this value to bool");
  return false; // to avoid warning
}

double StrToDouble(const std::string &s) {
  try {
    std::istringstream ss(s);
    ss.imbue(std::locale("C"));
    double result;
    ss >> result;

    if (ss.fail() || !ss.eof()) {
      throw std::runtime_error(
          "Invalid input string: cannot convert to double " + s);
    }

    return result;
  } catch (const std::invalid_argument &) {
    throw std::runtime_error("Invalid input string: cannot convert to double " +
                             s);
  } catch (const std::out_of_range &) {
    throw std::runtime_error(
        "Out of range: the value is out of range to store in a double " + s);
  }
}

int StrToInt(const std::string &s) {
  std::locale::global(std::locale("C"));
  try {
    return std::stoi(s);
  } catch (const std::invalid_argument &) {
    throw std::runtime_error(
        "Invalid input string: cannot convert to integer " + s);
  } catch (const std::out_of_range &) {
    throw std::runtime_error(
        "Out of range: the value is out of range to store in an integer " + s);
  }
}

G4ThreeVector StrToG4ThreeVector(const std::string &s) {
  G4ThreeVector n;
  std::string ls = s;
  std::replace(ls.begin(), ls.end(), '[', ' ');
  std::replace(ls.begin(), ls.end(), ']', ' ');
  std::istringstream f(ls);
  std::string v;
  int i = 0;
  while (getline(f, v, ',')) {
    n[i] = atof(v.c_str());
    i += 1;
  }
  return n;
}

std::vector<std::string>
GetVectorFromMapString(const std::map<std::string, std::string> &map_input,
                       const std::string &key) {
  std::vector<std::string> result;

  const auto it = map_input.find(key);
  if (it == map_input.end() || it->second.empty()) {
    return result;
  }

  std::string value = it->second;
  // Remove leading '[' and trailing ']'
  if (value.front() == '[' && value.back() == ']') {
    value = value.substr(1, value.length() - 2);
  }

  size_t pos = 0;
  while (pos < value.length()) {
    // Find the next quote
    pos = value.find('\'', pos);
    if (pos == std::string::npos)
      break;

    // Find the closing quote
    const size_t end = value.find('\'', pos + 1);
    if (end == std::string::npos)
      break;

    // Extract the string between quotes
    std::string item = value.substr(pos + 1, end - pos - 1);
    if (!item.empty()) {
      result.push_back(item);
    }

    pos = end + 1;
  }

  return result;
}

std::string ParamAt(const std::map<std::string, std::string> &param,
                    const std::string &key) {
  if (param.find(key) == param.end()) {
    // print all keys
    for (auto [fst, snd] : param) {
      DDD(fst);
      DDD(snd);
    }
    DDD(key);
    Fatal("Cannot find this key in the param list");
  }
  return param.at(key);
}