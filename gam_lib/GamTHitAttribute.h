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

    virtual void FillToRoot(size_t index) override;

    virtual void FillDValue(double v) override;

    virtual void FillSValue(std::string v) override;

    virtual void FillIValue(int v) override;

    virtual void Fill3Value(G4ThreeVector v) override;

    virtual void Clear() override;

protected:
    std::vector<T> fValues;
};

#include "GamTHitAttribute.icc"

#endif // GamTHitAttribute_h
