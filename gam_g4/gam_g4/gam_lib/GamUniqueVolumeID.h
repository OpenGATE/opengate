/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamUniqueVolumeID_h
#define GamUniqueVolumeID_h

#include <string>
#include "GamUniqueVolumeID.h"
#include "G4VTouchable.hh"
#include "G4VPhysicalVolume.hh"
#include "G4AffineTransform.hh"

/*
    Manage a unique ID for a given volume in the geometrical hierarchy.
    This is determined by the G4 touchable.
    The ID is a vector of int, with the CopyNb at each depth of the geometrical tree, starting from world.
    Information about volume name and transform are stored for convenience.

    A string fID, of the form 0_0_1_4 (with copyNb at all depth separated with _) is also computed.
 */

class GamUniqueVolumeID {
public:

    typedef std::shared_ptr<GamUniqueVolumeID> Pointer;

    typedef struct {
        std::string fVolumeName;
        int fCopyNb;
        int fDepth;
        G4AffineTransform fTransform;
        G4VPhysicalVolume *fVolume;

    } VolumeDepthID;

    GamUniqueVolumeID();

    GamUniqueVolumeID(const G4VTouchable *touchable);

    static Pointer New(const G4VTouchable *touchable = nullptr);

    friend std::ostream &operator<<(std::ostream &,
                                    const GamUniqueVolumeID::VolumeDepthID &v);

    std::vector<VolumeDepthID> fVolumeDepthID;

    std::string fID;

};


#endif // GamUniqueVolumeID_h
