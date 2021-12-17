/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitAttributeManager_h
#define GamHitAttributeManager_h

#include <pybind11/stl.h>
#include "GamVHitAttribute.h"
#include "GamHelpers.h"
#include "GamHitsCollection.h"


class GamHitAttributeManager {
    /*
     Singleton object.
     This class manages the list of available Attributes
     */
public:

    static GamHitAttributeManager *GetInstance();

    GamVHitAttribute *NewHitAttribute(std::string name);

    void DefineHitAttribute(std::string name, char type, GamVHitAttribute::ProcessHitsFunctionType f);

    std::string DumpAvailableHitAttributeNames();

protected:
    GamHitAttributeManager();

    static GamHitAttributeManager *fInstance;

    void InitializeAllHitAttributes();

    std::map<std::string, GamVHitAttribute *> fAvailableHitAttributes;

    GamVHitAttribute *CopyHitAttribute(GamVHitAttribute *);

};

#endif // GamHitAttributeManager_h
