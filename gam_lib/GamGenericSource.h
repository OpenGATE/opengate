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

    ~GamGenericSource();

    virtual void initialize(py::dict &user_info);

    virtual double PrepareNextTime(double current_simulation_time);

    virtual void GeneratePrimaries(G4Event *event, double time);

    int n;

protected:
    int max_n;
    //G4SingleParticleSource * m_sps;
    std::unique_ptr<G4SingleParticleSource> m_sps;
    double m_activity;
    void initialize_particle(py::dict &user_info);
    void initialize_position(py::dict user_info);
    void initialize_direction(py::dict user_info);
    void initialize_energy(py::dict user_info);
};

#endif // GamGenericSource_h
