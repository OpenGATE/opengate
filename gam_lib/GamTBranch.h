/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamTBranch_h
#define GamTBranch_h

#include <pybind11/stl.h>
#include "GamVActor.h"
#include "GamHelpers.h"
#include "GamVBranch.h"

template<class T>
class GamBranch : public GamVBranch {
public:
    GamBranch(std::string vname, char vtype) : GamVBranch(vname, vtype) {}

    virtual ~GamBranch();

    std::vector<T> values;

    std::vector<T> & GetValues() { return values; }

    virtual void CopyValues(GamVBranch *output, std::vector<unsigned long> &indexes);

    virtual void FillToRoot(G4RootAnalysisManager *am, unsigned long i);

    virtual unsigned long size() { return values.size(); }

};

#include "GamTBranch.icc"

#endif // GamTBranch_h
