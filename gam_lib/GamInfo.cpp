/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamInfo.h"
#include "G4Version.hh"
#include <itkVersion.h>


#ifdef G4MULTITHREADED

#include "G4MTRunManager.hh"

#else
#include "G4RunManager.hh"
#endif

bool GamInfo::get_G4MULTITHREADED() {
#ifdef G4MULTITHREADED
    return true;
#else
    return false;
#endif
}

std::string GamInfo::get_G4Version() {
    return G4Version;
}

std::string GamInfo::get_G4Date() {
    return G4Date;
}

std::string GamInfo::get_ITKVersion() {
    return itk::Version::GetITKVersion();
}

