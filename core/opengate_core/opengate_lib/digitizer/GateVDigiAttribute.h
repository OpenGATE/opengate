/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVDigiAttribute_h
#define GateVDigiAttribute_h

#include "../GateHelpers.h"
#include "../GateUniqueVolumeID.h"

class GateVDigiAttribute {
public:
  GateVDigiAttribute(const std::string &vname, char vtype);

  virtual ~GateVDigiAttribute();

  void ProcessHits(G4Step *step);

  virtual std::vector<double> &GetDValues();

  virtual std::vector<int> &GetIValues();

  virtual std::vector<int64_t> &GetLValues();

  virtual std::vector<std::string> &GetSValues();

  virtual std::vector<G4ThreeVector> &Get3Values();

  virtual std::vector<GateUniqueVolumeID::Pointer> &GetUValues();

  virtual void FillToRoot(size_t) const {}

  virtual void FillDValue(double) {}

  virtual void FillSValue(std::string) {}

  virtual void FillIValue(int) {}

  virtual void FillLValue(int64_t) {}

  virtual void Fill3Value(G4ThreeVector) {}

  virtual void FillUValue(GateUniqueVolumeID::Pointer) {}

  virtual void Fill(GateVDigiAttribute * /*unused*/, size_t /*unused*/) {}

  virtual void FillDigiWithEmptyValue();

  virtual int GetSize() const = 0;

  virtual void Clear() = 0;

  void SetDigiAttributeId(int id) { fDigiAttributeId = id; }

  void SetTupleId(int id) { fTupleId = id; }

  std::string GetDigiAttributeName() const { return fDigiAttributeName; }

  virtual std::string Dump(int i) const = 0;

  char GetDigiAttributeType() const { return fDigiAttributeType; }

  int GetDigiAttributeId() const { return fDigiAttributeId; }

  int GetDigiAttributeTupleId() const { return fTupleId; }

  // Main function performing the process hit
  typedef std::function<void(GateVDigiAttribute *b, G4Step *)>
      ProcessHitsFunctionType;
  ProcessHitsFunctionType fProcessHitsFunction;

protected:
  // Name of the attribute (e.g. "KineticEnergy")
  std::string fDigiAttributeName;

  // Attribute type as a single character: D I L S 3
  char fDigiAttributeType;

  // Attribute index in a given DigiCollection
  G4int fDigiAttributeId;

  // Index of the DigiCollection in the root tree
  G4int fTupleId;
};

#endif // GateVDigiAttribute_h
