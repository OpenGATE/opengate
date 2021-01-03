/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamGenericSource_h
#define GamGenericSource_h

#include <pybind11/stl.h>
#include "G4SingleParticleSource.hh"
#include "GamVSource.h"

namespace py = pybind11;

class GamGenericSource : public GamVSource {

public:

    virtual void CleanInThread();

    virtual void InitializeUserInfo(py::dict &user_info);

    virtual double PrepareNextTime(double current_simulation_time);

    virtual void GeneratePrimaries(G4Event *event, double time);

    int fN;

protected:
    int fMaxN;
    // We do not used a std::unique_ptr to control the deletion during the CleanInThread
    G4SingleParticleSource *fSPS;
    double fActivity;

    void InitializeParticle(py::dict &user_info);

    void InitializePosition(py::dict user_info);

    void InitializeDirection(py::dict user_info);

    void InitializeEnergy(py::dict user_info);
};

#endif // GamGenericSource_h
