/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateUniqueVolumeID_h
#define GateUniqueVolumeID_h

#include "G4AffineTransform.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VTouchable.hh"
#include <array>
#include <cstdint> // Required for uint64_t
#include <map>
#include <memory>
#include <string>
#include <vector>

/*
    Manage a unique ID for a given volume in the geometrical hierarchy.
    This is determined by the G4 touchable.
    The ID is a vector of int, with the CopyNb at each depth of the geometrical
   tree, starting from world. Information about volume name and transform are
   stored for convenience.

    A string fID, of the form 0_0_1_4 (with copyNb at all depth separated with
   _) is also computed.
 */

class GateUniqueVolumeID {
public:
  // Shared pointer
  typedef std::shared_ptr<GateUniqueVolumeID> Pointer;

  // Internal structure to keep information at each depth level
  // in the volume hierarchy
  typedef struct {
    std::string fVolumeName;
    int fCopyNb;
    int fDepth;
    G4ThreeVector fTranslation;
    G4RotationMatrix fRotation;
    G4VPhysicalVolume *fVolume;

  } VolumeDepthID;

  // Fixed sized array of CopyNo for all depth levels
  static const int MaxDepth = 15;
  typedef std::array<int, MaxDepth> IDArrayType;

  GateUniqueVolumeID();

  ~GateUniqueVolumeID();

  explicit GateUniqueVolumeID(const G4VTouchable *touchable,
                              bool debug = false);

  static IDArrayType ComputeArrayID(const G4VTouchable *touchable);

  static Pointer New(const G4VTouchable *touchable = nullptr,
                     bool debug = false);

  const std::vector<VolumeDepthID> &GetVolumeDepthID() const;

  size_t GetDepth() const { return fVolumeDepthID.size(); }

  uint64_t GetNumericID() const { return fNumericID; }

  static std::string ArrayIDToStr(IDArrayType id);

  friend std::ostream &operator<<(std::ostream &,
                                  const GateUniqueVolumeID::VolumeDepthID &v);

  G4AffineTransform *GetLocalToWorldTransform(size_t depth);

  G4AffineTransform *GetWorldToLocalTransform(size_t depth);

  // Get the string ID for a given depth (uses an internal cache)
  std::string GetIdUpToDepth(int depth) const;

  // Get the hashed ID for a given depth (uses an internal cache)
  uint64_t GetIdUpToDepthAsHash(int depth) const;

  std::vector<VolumeDepthID> fVolumeDepthID;
  IDArrayType fArrayID{};
  std::string fID;
  uint64_t fNumericID;

  // Caches for strings and their hashes, mutable to allow modification in const
  // methods
  mutable std::map<int, std::string> fCachedIdDepth;
  mutable std::map<int, uint64_t> fCachedIdDepthHash;
};

#endif // GateUniqueVolumeID_h
