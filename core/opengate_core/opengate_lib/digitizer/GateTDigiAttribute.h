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

  ~GateTDigiAttribute() override;

  virtual int GetSize() const override;

  virtual std::vector<double> &GetDValues() override;

  virtual std::vector<int> &GetIValues() override;

  virtual std::vector<std::string> &GetSValues() override;

  virtual std::vector<G4ThreeVector> &Get3Values() override;

  virtual std::vector<GateUniqueVolumeID::Pointer> &GetUValues() override;

  const std::vector<T> &GetValues() const;

  virtual void FillToRoot(size_t index) const override;

  virtual void FillDValue(double v) override;

  virtual void FillSValue(std::string v) override;

  virtual void FillIValue(int v) override;

  virtual void Fill3Value(G4ThreeVector v) override;

  virtual void FillUValue(GateUniqueVolumeID::Pointer v) override;

  virtual void Fill(GateVDigiAttribute *input, size_t index) override;

  virtual void FillDigiWithEmptyValue() override;

  virtual void Clear() override;

  virtual std::string Dump(int i) const override;

protected:
  struct threadLocal_t {
    std::vector<T> fValues;
  };
  G4Cache<threadLocal_t> threadLocalData;

  void InitDefaultProcessHitsFunction();
};

#endif // GateTDigiAttribute_h
