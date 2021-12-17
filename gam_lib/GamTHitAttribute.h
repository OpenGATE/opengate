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
    explicit GamTHitAttribute(const std::string vname);

    ~GamTHitAttribute() override;

    void FillDValue(double v) override;

    virtual void FillSValue(std::string v) override;

    virtual void FillIValue(int v) override;

    virtual void Fill3Value(G4ThreeVector v) override;

};

#include "GamTHitAttribute.icc"

#endif // GamTHitAttribute_h
