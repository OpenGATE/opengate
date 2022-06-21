/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamKineticEnergyFilter_h
#define GamKineticEnergyFilter_h

#include <pybind11/stl.h>
#include "GamVFilter.h"

namespace py = pybind11;

class GamKineticEnergyFilter : public GamVFilter {

public:

    GamKineticEnergyFilter() : GamVFilter() {}

    void Initialize(py::dict &user_info) override;

    // To avoid gcc -Woverloaded-virtual
    // https://stackoverflow.com/questions/9995421/gcc-woverloaded-virtual-warnings
    using GamVFilter::Accept;

    bool Accept(const G4Step *step) const override;

    double fEnergyMin;
    double fEnergyMax;
};

#endif // GamKineticEnergyFilter_h
