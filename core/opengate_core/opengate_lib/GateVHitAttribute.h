/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVHitAttribute_h
#define GateVHitAttribute_h

#include "G4TouchableHistory.hh"
#include "GateHelpers.h"
#include "GateUniqueVolumeID.h"
#include <pybind11/stl.h>

class GateVHitAttribute {
public:
  GateVHitAttribute(std::string vname, char vtype);

  virtual ~GateVHitAttribute();

  void ProcessHits(G4Step *step);

  virtual std::vector<double> &GetDValues();

  virtual std::vector<int> &GetIValues();

  virtual std::vector<std::string> &GetSValues();

  virtual std::vector<G4ThreeVector> &Get3Values();

  virtual std::vector<GateUniqueVolumeID::Pointer> &GetUValues();

  virtual void FillToRoot(size_t) const {}

  virtual void FillDValue(double) {}

  virtual void FillSValue(std::string) {}

  virtual void FillIValue(int) {}

  virtual void Fill3Value(G4ThreeVector) {}

  virtual void FillUValue(GateUniqueVolumeID::Pointer) {}

  virtual void Fill(GateVHitAttribute * /*unused*/, size_t /*unused*/) {}

  virtual void FillHitWithEmptyValue();

  virtual int GetSize() const = 0;

  virtual void Clear() = 0;

  void SetHitAttributeId(int id) { fHitAttributeId = id; }

  void SetTupleId(int id) { fTupleId = id; }

  std::string GetHitAttributeName() const { return fHitAttributeName; }

  virtual std::string Dump(int i) const = 0;

  char GetHitAttributeType() const { return fHitAttributeType; }

  int GetHitAttributeId() const { return fHitAttributeId; }

  int GetHitAttributeTupleId() const { return fTupleId; }

  // Main function performing the process hit
  typedef std::function<void(GateVHitAttribute *b, G4Step *)>
      ProcessHitsFunctionType;
  ProcessHitsFunctionType fProcessHitsFunction;

protected:
  // Name of the attribute (e.g. "KineticEnergy")
  std::string fHitAttributeName;

  // Attribute type as a single character : D I S 3
  char fHitAttributeType;

  // Attribute index in a given HitCollection
  G4int fHitAttributeId;

  // Index of the HitCollection in the root tree
  G4int fTupleId;
};

#endif // GateVHitAttribute_h
