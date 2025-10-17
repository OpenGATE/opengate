/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateUniqueVolumeID_h
#define GateUniqueVolumeID_h

#include "G4VPhysicalVolume.hh"
#include "G4VTouchable.hh"
#include "GateHelpers.h"
#include <array>
#include <map>
#include <memory>
#include <string>

/*
    Manage a unique ID for a given volume in the geometrical hierarchy.
    This is determined by the G4 touchable.
    The ID is a vector of int, with the CopyNb at each depth of the geometrical
   tree, starting from the world.
   Information about volume name and transform are stored in the touchable
   G4NavigationHistory.

    A string fID, of the form 0_0_1_4 (with copyNb at all depth separated with
   _) is also computed.
 */

class GateUniqueVolumeID {
public:
  // Shared pointer type
  typedef std::shared_ptr<GateUniqueVolumeID> Pointer;

  // Fixed sized array of CopyNo for all depth levels
  static constexpr int MaxDepth = 15;
  typedef std::array<int, MaxDepth> IDArrayType;

  GateUniqueVolumeID();

  ~GateUniqueVolumeID();

  explicit GateUniqueVolumeID(const G4VTouchable *touchable,
                              bool debug = false);

  static IDArrayType ComputeArrayID(const G4VTouchable *touchable);

  // Compute the string ID from a touchable without creating a full object
  static std::string ComputeStringID(const G4VTouchable *touchable);

  static Pointer New(const G4VTouchable *touchable = nullptr,
                     bool debug = false);

  size_t GetDepth() const { return fTouchable.GetDepth(); }

  int GetNumericID() const { return fNumericID; }

  static std::string ArrayIDToStr(const IDArrayType &id);

  G4VPhysicalVolume *GetTopPhysicalVolume() const;

  // Get the string ID for a given depth (uses an internal cache)
  std::string GetIdUpToDepth(int depth) const;

  // Get the hashed ID for a given depth (uses an internal cache)
  int GetIdUpToDepthAsHash(int depth) const;

  IDArrayType fArrayID{};
  std::string fID;
  int fNumericID;
  G4NavigationHistory fTouchable;

  // Caches for strings and their hashes, mutable to allow modification in const
  // methods
  mutable std::map<int, std::string> fCachedIdDepth;
  mutable std::map<int, int> fCachedIdDepthHash;
};

#endif // GateUniqueVolumeID_h
