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
#include "GamSingleParticleSource.h"

namespace py = pybind11;

class GamGenericSource : public GamVSource {

public:

    GamGenericSource();

    virtual ~GamGenericSource();

    virtual void CleanInThread();

    virtual void InitializeUserInfo(py::dict &user_info);

    virtual double PrepareNextTime(double current_simulation_time);

    virtual void GeneratePrimaries(G4Event *event, double time);

    int fN;

protected:
    int fMaxN;
    // We cannot not use a std::unique_ptr
    // (or maybe by controling the deletion during the CleanInThread ?)
    GamSingleParticleSource *fSPS;

    double fActivity;
    bool fIsGenericIon;
    int fA; // A: Atomic Mass (nn + np +nlambda)
    int fZ; // Z: Atomic Number
    double fE; // E: Excitation energy

    void InitializeParticle(py::dict &user_info);

    void InitializeIon(py::dict &user_info);

    void InitializePosition(py::dict user_info);

    void InitializeDirection(py::dict user_info);

    void InitializeEnergy(py::dict user_info);

};

#endif // GamGenericSource_h
