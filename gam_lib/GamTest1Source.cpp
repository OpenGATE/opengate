/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamTest1Source.h"
#include "G4RandomTools.hh"

void GamTest1Source::initialize(py::dict &user_info) {
    std::cout << "initialize  GamTest1Source " << std::endl;
    std::cout << "dict: " << user_info.size() << std::endl;
    GamVSource::initialize(user_info);
    m_particle_gun = new G4ParticleGun(1);
    auto particle_table = G4ParticleTable::GetParticleTable();
    auto particle = particle_table->FindParticle("gamma");
    m_particle_gun->SetParticleDefinition(particle);
    m_particle_gun->SetParticleMomentumDirection(G4ThreeVector(0., 0., 1.));
    m_particle_gun->SetParticleEnergy(80 * CLHEP::keV);
    m_particle_gun->SetParticleTime(0.0);
    n = 0;
}

double GamTest1Source::PrepareNextTime(double /*current_simulation_time*/) {
    std::cout << "GamTest1Source::PrepareNextTime" << std::endl;
    if (n > 10) return -1;
    return 0; // FIXME start
}


void GamTest1Source::GeneratePrimaries(G4Event *event, double current_simulation_time) {
    //std::cout << "generate " << time << std::endl;
    auto diameter = 20.0 * CLHEP::mm;
    auto x0 = diameter * (G4UniformRand() - 0.5);
    auto y0 = diameter * (G4UniformRand() - 0.5);
    auto z0 = 0.0;
    // std::cout << "xyz " << x0 << " " << y0 << " " << z0 << std::endl;
    m_particle_gun->SetParticlePosition(G4ThreeVector(x0, y0, z0));
    m_particle_gun->SetParticleTime(current_simulation_time);
    m_particle_gun->GeneratePrimaryVertex(event);
    n++;
}