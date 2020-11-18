/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "G4UnitsTable.hh"
#include "GamTest1Source.h"

void GamTest1Source::initialize(py::dict &user_info) {
    GamVSource::initialize(user_info);
    // get the user info
    std::string pname = py::str(user_info["particle"]);
    max_n = py::int_(user_info["n"]);
    double e = py::float_(user_info["energy"]);
    diameter = py::float_(user_info["diameter"]);
    radius = diameter / 2.0;
    auto t = py::list(user_info["translation"]);
    translation.setX(py::float_(t[0]));
    translation.setY(py::float_(t[1]));
    translation.setZ(py::float_(t[2]));
    activity = py::float_(user_info["activity"]);
    // Create the gun
    m_particle_gun = new G4ParticleGun(1);
    auto particle_table = G4ParticleTable::GetParticleTable();
    auto particle = particle_table->FindParticle(pname);
    if (particle == nullptr) {
        Fatal("Cannot find the particle '" + pname + "'.");
    }
    m_particle_gun->SetParticleDefinition(particle);
    m_particle_gun->SetParticleMomentumDirection(G4ThreeVector(0., 0., 1.));
    m_particle_gun->SetParticleEnergy(e);
    m_particle_gun->SetParticleTime(0.0);
    n = 0;
    position.setZ(translation.z());
}

double GamTest1Source::PrepareNextTime(double current_simulation_time) {
    // activity case
    if (max_n <= 0) {
        if (current_simulation_time < start_time)
            return start_time;
        if (current_simulation_time >= end_time)
            return -1;
        double next_time = current_simulation_time - log(G4UniformRand()) * (1.0 / activity);
        return next_time;
    }
    // number of particle case
    if (n >= max_n) return -1;
    return start_time;
}


void GamTest1Source::GeneratePrimaries(G4Event *event, double current_simulation_time) {
    GamVSource::GeneratePrimaries(event, current_simulation_time);
    auto length = sqrt(G4UniformRand()) * radius;
    auto angle = M_PI * G4UniformRand() * 2;
    position.setX(length * cos(angle) + translation.x());
    position.setY(length * sin(angle) + translation.y());
    m_particle_gun->SetParticlePosition(position);
    m_particle_gun->SetParticleTime(current_simulation_time);
    m_particle_gun->GeneratePrimaryVertex(event);
    //std::cout << name << " " << n << " " << G4BestUnit(current_simulation_time, "Time") << std::endl;
    n++;
}