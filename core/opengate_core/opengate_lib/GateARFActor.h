/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateARFActor_h
#define GateARFActor_h

#include <pybind11/stl.h>
#include "GateVActor.h"
#include "GateHelpers.h"

namespace py = pybind11;

class GateARFActor : public GateVActor {

public:

    // Callback function
    using ARFFunctionType = std::function<void(GateARFActor *)>;

    // Constructor
    explicit GateARFActor(py::dict &user_info);

    // Main function called every step in attached volume
    void SteppingAction(G4Step *) override;

    // set the user "apply" function (python)
    void SetARFFunction(ARFFunctionType &f);

    // need public because exposed to Python
    std::vector<double> fEnergy;
    std::vector<double> fPositionX;
    std::vector<double> fPositionY;
    std::vector<double> fDirectionX;
    std::vector<double> fDirectionY;

    // number of particle hitting the detector
    int fCurrentNumberOfHits;

protected:
    int fBatchSize;
    ARFFunctionType fApply;

};

#endif // GateARFActor_h
