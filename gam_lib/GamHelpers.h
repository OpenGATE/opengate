/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHelpers_h
#define GamHelpers_h

#include <iostream>
#include <pybind11/stl.h>
#include <G4ThreeVector.hh>

namespace py = pybind11;

void Fatal(const std::string s);

#define DD(a) std::cout << #a << " = [ " << a << " ]\n";

#define DDD(a) { std::cout << "GAM [" << G4Threading::G4GetThreadId() << "] (" << __func__ << ") ==> " << #a << " = [ " << a << " ]\n"; }

#define DDDV(a) { std::cout << "GAM [" << G4Threading::G4GetThreadId() << "] (" << __func__ << ") ==> " << #a; for (auto _i=0; _i<a.size(); _i++) std::cout << a[_i] << " "; std::cout << "\n"; }


#endif // GamHelpers_h
