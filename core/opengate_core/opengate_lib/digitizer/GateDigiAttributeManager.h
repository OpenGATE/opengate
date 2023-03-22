/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigiAttributeManager_h
#define GateDigiAttributeManager_h

#include "../GateHelpers.h"
#include "GateDigiCollection.h"
#include "GateVDigiAttribute.h"
#include <pybind11/stl.h>

class GateDigiAttributeManager {
  /*
   Singleton object.
   This class manages the list of all available DigiAttributes.

   This list of available attributes is in GateDigiAttributeList.cpp.
   This list is created with DefineDigiAttribute.

   Once a HitsCollection considers an attribute with GetDigiAttribute
   it is copied (CopyDigiAttribute) from the list of available attributes.

   */
public:
  static GateDigiAttributeManager *GetInstance();

  GateVDigiAttribute *GetDigiAttribute(std::string name);

  void
  DefineDigiAttribute(std::string name, char type,
                      const GateVDigiAttribute::ProcessHitsFunctionType &f);

  std::string DumpAvailableDigiAttributeNames();
  std::vector<std::string> GetAvailableDigiAttributeNames();

  GateVDigiAttribute *GetDigiAttributeByName(const std::string &name);

  GateVDigiAttribute *CopyDigiAttribute(GateVDigiAttribute *);

protected:
  GateDigiAttributeManager();

  static GateDigiAttributeManager *fInstance;

  void InitializeAllDigiAttributes();

  std::map<std::string, GateVDigiAttribute *> fAvailableDigiAttributes;
};

#endif // GateDigiAttributeManager_h
