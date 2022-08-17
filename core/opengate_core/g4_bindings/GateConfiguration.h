/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateConfiguration_h
#define GateConfiguration_h

#define G4VIS_USE 1
#define G4UI_USE 1
#define G4UI_USE_QT 1


#ifdef G4UI_USE_QT
// nothing
#else
Should never be here
#endif

#ifdef G4VIS_USE
// nothing
#else
Should never be here
#endif

#ifdef G4UI_USE
// nothing
#else
Should never be here
#endif

#endif // GateConfiguration_h
