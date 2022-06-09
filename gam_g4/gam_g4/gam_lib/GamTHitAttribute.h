/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamTHitAttribute_h
#define GamTHitAttribute_h

#include <pybind11/stl.h>
#include "GamHelpers.h"
#include "GamVHitAttribute.h"
#include "GamUniqueVolumeID.h"

template<class T>
class GamTHitAttribute : public GamVHitAttribute {
public:
    explicit GamTHitAttribute(std::string vname);

    ~GamTHitAttribute() override;

    virtual int GetSize() const override;

    virtual std::vector<double> &GetDValues() override;

    virtual std::vector<int> &GetIValues() override;

    virtual std::vector<std::string> &GetSValues() override;

    virtual std::vector<G4ThreeVector> &Get3Values() override;

    virtual std::vector<GamUniqueVolumeID::Pointer> &GetUValues() override;

    const std::vector<T> &GetValues() const;

    virtual void FillToRoot(size_t index) const override;

    virtual void FillDValue(double v) override;

    virtual void FillSValue(std::string v) override;

    virtual void FillIValue(int v) override;

    virtual void Fill3Value(G4ThreeVector v) override;

    virtual void FillUValue(GamUniqueVolumeID::Pointer v) override;

    virtual void Fill(GamVHitAttribute *input, size_t index) override;

    virtual void FillHitWithEmptyValue() override;

    virtual void Clear() override;

    virtual std::string Dump(int i) const;

protected:
    struct threadLocal_t {
        std::vector<T> fValues;
    };
    G4Cache<threadLocal_t> threadLocalData;

};

#include "GamTHitAttribute.icc"

#endif // GamTHitAttribute_h
