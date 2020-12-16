/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "G4UnitsTable.hh"
#include "G4SingleParticleSource.hh"
#include "GamGenericSource.h"
#include "GamDictHelpers.h"

#include <pybind11/numpy.h>

void GamGenericSource::initialize(py::dict &user_info) {
    GamVSource::initialize(user_info);

    // gun
    //m_sps = new G4SingleParticleSource();
    m_sps = std::make_unique<G4SingleParticleSource>();
    DDD(m_sps);

    // get the user info for the particle
    initialize_particle(user_info);

    // get user info about activity or nb of events
    max_n = dict_int(user_info, "n");
    m_activity = dict_float(user_info, "activity");
    // FIXME check here if not both
    // FIXME -> add decay

    // position, direction, energy
    initialize_position(py::dict(user_info["position"]));
    initialize_direction(py::dict(user_info["direction"]));
    initialize_energy(py::dict(user_info["energy"]));

    // confine //FIXME later

    // init number of events
    n = 0;
}

double GamGenericSource::PrepareNextTime(double current_simulation_time) {
    // activity case
    if (max_n <= 0) {
        if (current_simulation_time < start_time)
            return start_time;
        if (current_simulation_time >= end_time)
            return -1;
        double next_time = current_simulation_time - log(G4UniformRand()) * (1.0 / m_activity);
        return next_time;
    }
    // number of particle case
    if (n >= max_n) return -1;
    return start_time;
}


void GamGenericSource::GeneratePrimaries(G4Event *event, double current_simulation_time) {
    GamVSource::GeneratePrimaries(event, current_simulation_time);
    m_sps->SetParticleTime(current_simulation_time);
    m_sps->GeneratePrimaryVertex(event);
    std::ostringstream oss;
    oss << event->GetEventID() << " "  << G4BestUnit(current_simulation_time, "Time");
    DDD(oss.str());
    //DDD(n);
    // std::cout << name << " " << n << " " << G4BestUnit(current_simulation_time, "Time") << std::endl;
    n++;
}

void GamGenericSource::initialize_particle(py::dict &user_info) {
    std::string pname = py::str(user_info["particle"]);
    // FIXME -> add ion A and Z ; charge ; polarization
    auto particle_table = G4ParticleTable::GetParticleTable();
    auto particle = particle_table->FindParticle(pname);
    if (particle == nullptr) {
        Fatal("Cannot find the particle '" + pname + "'.");
    }
    m_sps->SetParticleDefinition(particle);
}

void GamGenericSource::initialize_position(py::dict user_info) {
    /* G4:
     * pos_types = ['Point', 'Beam', 'Plane', 'Surface', 'Volume']
     * shape_types = ['Square', 'Circle', 'Annulus', 'Ellipse', 'Rectangle',
                       'Sphere', 'Ellipsoid', 'Cylinder', 'Right', 'NULL']
    * New interface -> point box sphere disc (later: ellipse)
    * center rotation size radius
    */
    auto pos = m_sps->GetPosDist();
    auto pos_type = dict_str(user_info, "type");
    std::vector<std::string> l = {"sphere", "point", "box", "disc"};
    check_is_in(pos_type, l);
    auto center = dict_vec(user_info, "center");
    if (pos_type == "point") {
        pos->SetPosDisType("Point");
    }
    if (pos_type == "box") {
        pos->SetPosDisType("Volume");
        pos->SetPosDisShape("Para");
        auto size = dict_vec(user_info, "size") / 2.0;
        pos->SetHalfX(size[0]);
        pos->SetHalfY(size[1]);
        pos->SetHalfZ(size[2]);
    }
    if (pos_type == "sphere") {
        pos->SetPosDisType("Volume");
        pos->SetPosDisShape("Sphere");
        auto radius = dict_float(user_info, "radius");
        pos->SetRadius(radius);
    }
    if (pos_type == "disc") {
        pos->SetPosDisType("Plane");
        pos->SetPosDisShape("Circle");
        auto radius = dict_float(user_info, "radius");
        pos->SetRadius(radius);
    }
    // position center
    pos->SetCentreCoords(center);
    // rotation
    auto rotation = dict_matrix(user_info, "rotation");
    G4ThreeVector r1(*rotation.data(0, 0),
                     *rotation.data(0, 1),
                     *rotation.data(0, 2));
    G4ThreeVector r2(*rotation.data(1, 0),
                     *rotation.data(1, 1),
                     *rotation.data(1, 2));
    pos->SetPosRot1(r1);
    pos->SetPosRot2(r2);
}

void GamGenericSource::initialize_direction(py::dict user_info) {
    /*
     * G4: iso, cos, beam  and user for isotropic, cosine-law, beam and user-defined
     *
     * New ones: iso, focus, direction
     * (Later: beam, user defined)
     */
    auto ang = m_sps->GetAngDist();
    auto ang_type = dict_str(user_info, "type");
    std::vector<std::string> l = {"iso", "momentum", "focused"};
    check_is_in(ang_type, l);
    if (ang_type == "iso") {
        ang->SetAngDistType("iso");
    }
    if (ang_type == "momentum") {
        ang->SetAngDistType("planar"); // FIXME really ??
        auto d = dict_vec(user_info, "momentum");
        ang->SetParticleMomentumDirection(d);
    }
    if (ang_type == "focused") {
        ang->SetAngDistType("focused");
        auto f = dict_vec(user_info, "focus_point");
        ang->SetFocusPoint(f);
    }
}

void GamGenericSource::initialize_energy(py::dict user_info) {
    /*
     * G4: Mono (mono-energetic), Lin (linear), Pow (power-law), Exp
     * (exponential), Gauss (gaussian), Brem (bremsstrahlung), BBody (black-body), Cdg
     * (cosmic diffuse gamma-ray), User (user-defined), Arb (arbitrary
     * point-wise), Epn (energy per nucleon).
     *
     * New interface: mono gauss // FIXME later 'user'
     *
     */
    auto ene = m_sps->GetEneDist();
    auto ene_type = dict_str(user_info, "type");
    std::vector<std::string> l = {"mono", "gauss"};
    check_is_in(ene_type, l);
    if (ene_type == "mono") {
        ene->SetEnergyDisType("Mono");
        auto e = dict_float(user_info, "mono");
        ene->SetMonoEnergy(e);
    }
    if (ene_type == "gauss") {
        ene->SetEnergyDisType("Gauss");
        auto e = dict_float(user_info, "mono");
        ene->SetMonoEnergy(e);
        auto g = dict_float(user_info, "sigma_gauss");
        ene->SetBeamSigmaInE(g);
    }
}
