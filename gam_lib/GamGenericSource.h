/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamGenericSource_h
#define GamGenericSource_h

#include <pybind11/stl.h>
#include "GamVSource.h"
#include "GamSingleParticleSource.h"

namespace py = pybind11;

class GamGenericSource : public GamVSource {

public:

    GamGenericSource();

    virtual ~GamGenericSource();

    virtual void CleanWorkerThread();

    virtual void InitializeUserInfo(py::dict &user_info);

    virtual double PrepareNextTime(double current_simulation_time);

    virtual void PrepareNextRun();

    virtual void GeneratePrimaries(G4Event *event, double time);

    /// Current number of simulated event in this source
    int fN;

    /// if acceptance angle, this variable store the total number of trials
    unsigned long fSkippedParticles;


protected:
    int fMaxN;
    // We cannot not use a std::unique_ptr
    // (or maybe by controlling the deletion during the CleanWorkerThread ?)
    GamSingleParticleSource *fSPS;

    double fActivity;
    double fInitialActivity;
    double fHalfLife;
    double fLambda;

    // generic ion is controlled separately (maybe initialized once Run is started)
    bool fIsGenericIon;
    int fA; // A: Atomic Mass (nn + np +nlambda)
    int fZ; // Z: Atomic Number
    double fE; // E: Excitation energy
    double fWeight;
    double fWeightSigma;

    // if confine is used, must be defined after the initialization
    bool fInitConfine;
    std::string fConfineVolume;

    virtual void InitializeParticle(py::dict &user_info);

    virtual void InitializeIon(py::dict &user_info);

    virtual void InitializePosition(py::dict user_info);

    virtual void InitializeDirection(py::dict user_info);

    virtual void InitializeEnergy(py::dict user_info);

    virtual void UpdateActivity(double time);

};

#endif // GamGenericSource_h
