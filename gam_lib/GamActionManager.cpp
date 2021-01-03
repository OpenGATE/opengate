/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamActionManager.h"
#include "GamSourceManager.h"
#include "GamHelpers.h"

GamActionManager::GamActionManager() {
    DD("GamActionManager Constructor");
}


GamActionManager::~GamActionManager() {
    DD("GamActionManager Destructor");
}

void GamActionManager::Build() const {
    DD("GamActionManager Build");

    // self.source_manager.build()
    //auto sm = new GamSourceManager();
    // self.SetUserAction(p)
    //SetUserAction(sm);

}

void GamActionManager::BuildForMaster() const {
    DD("GamActionManager BuildForMaster");
}
