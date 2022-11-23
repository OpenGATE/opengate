/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitAttributeManager_h
#define GateHitAttributeManager_h

#include "GateHelpers.h"
#include "GateHitsCollection.h"
#include "GateVHitAttribute.h"
#include <pybind11/stl.h>

class GateHitAttributeManager {
  /*
   Singleton object.
   This class manages the list of all available HitAttributes.

   This list of available attributes is in GateHitAttributeList.cpp.
   This list is created with DefineHitAttribute.

   Once a HitsCollection considers an attribute with NewHitAttribute
   it is copied (CopyHitAttribute) from the list of available attributes.

   */
public:
  static GateHitAttributeManager *GetInstance();

  GateVHitAttribute *NewHitAttribute(std::string name);

  void DefineHitAttribute(std::string name, char type,
                          const GateVHitAttribute::ProcessHitsFunctionType &f);

  std::string DumpAvailableHitAttributeNames();
  std::vector<std::string> GetAvailableHitAttributeNames();

  GateVHitAttribute *GetHitAttributeByName(const std::string &name);

protected:
  GateHitAttributeManager();

  static GateHitAttributeManager *fInstance;

  void InitializeAllHitAttributes();

  std::map<std::string, GateVHitAttribute *> fAvailableHitAttributes;

  GateVHitAttribute *CopyHitAttribute(GateVHitAttribute *);
};

#endif // GateHitAttributeManager_h
