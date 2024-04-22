/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHelpers.h"

class GateInfo {
public:
  static bool get_G4MULTITHREADED();

  static std::string get_G4Version();

  static std::string get_G4Date();

  static std::string get_ITKVersion();

  static bool get_G4GDML();

  static void test();
};
