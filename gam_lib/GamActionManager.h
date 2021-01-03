/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamActionManager_h
#define GamActionManager_h

#include "G4VUserActionInitialization.hh"
//#include "GamSourceManager.h"

class GamActionManager : public G4VUserActionInitialization {
public:

    GamActionManager();

    virtual ~GamActionManager();

    virtual void Build() const;

    virtual void BuildForMaster() const;

    //GamSourceManager * fSourceManager;

};

#endif // GamActionManager_h
