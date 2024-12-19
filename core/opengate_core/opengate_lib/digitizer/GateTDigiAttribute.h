/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTDigiAttribute_h
#define GateTDigiAttribute_h

#include "../GateHelpers.h"
#include "../GateUniqueVolumeID.h"
#include "GateVDigiAttribute.h"
#include <pybind11/stl.h>

template <class T> class GateTDigiAttribute : public GateVDigiAttribute {
public:
  explicit GateTDigiAttribute(std::string vname);

  int GetSize() const override;

  std::vector<double> &GetDValues() override;

  std::vector<int> &GetIValues() override;

  std::vector<std::string> &GetSValues() override;

  std::vector<G4ThreeVector> &Get3Values() override;

  std::vector<GateUniqueVolumeID::Pointer> &GetUValues() override;

  const std::vector<T> &GetValues() const;

  void FillToRoot(size_t index) const override;

  void FillDValue(double v) override;

  void FillSValue(std::string v) override;

  void FillIValue(int v) override;

  void Fill3Value(G4ThreeVector v) override;

  void FillUValue(GateUniqueVolumeID::Pointer v) override;

  void Fill(GateVDigiAttribute *input, size_t index) override;

  void FillDigiWithEmptyValue() override;

  void Clear() override;

  std::string Dump(int i) const override;

protected:
  struct threadLocal_t {
    std::vector<T> fValues;
  };
  G4Cache<threadLocal_t> threadLocalData;

  void InitDefaultProcessHitsFunction();
};

#endif // GateTDigiAttribute_h
