/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "G4SingleParticleSource.hh"
#include "G4IonTable.hh"
#include "G4IonConstructor.hh"
#include "G4GenericIon.hh"
#include "GamGenericSource.h"
#include "GamDictHelpers.h"
#include "G4UnitsTable.hh"

#include <pybind11/numpy.h>

void GamGenericSource::CleanInThread() {
    // delete the fSPS (by the thread that create it)
    // delete fSPS;
    DDD("destructor generic source");
}

void GamGenericSource::InitializeUserInfo(py::dict &user_info) {
    GamVSource::InitializeUserInfo(user_info);

    // gun
    fSPS = new G4SingleParticleSource();

    // get the user info for the particle
    InitializeParticle(user_info);

    // get user info about activity or nb of events
    fMaxN = DictInt(user_info, "n");
    fActivity = DictFloat(user_info, "activity");
    // FIXME check here if not both
    // FIXME -> add decay

    // position, direction, energy
    InitializePosition(py::dict(user_info["position"]));
    InitializeDirection(py::dict(user_info["direction"]));
    InitializeEnergy(py::dict(user_info["energy"]));

    // confine //FIXME later

    // init number of events
    fN = 0;
}

double GamGenericSource::PrepareNextTime(double current_simulation_time) {
    // activity case
    if (fMaxN <= 0) {
        if (current_simulation_time < fStartTime)
            return fStartTime;
        if (current_simulation_time >= fEndTime)
            return -1;
        double next_time = current_simulation_time - log(G4UniformRand()) * (1.0 / fActivity);
        return next_time;
    }
    // number of particle case
    if (fN >= fMaxN) return -1;
    return fStartTime;
}


void GamGenericSource::GeneratePrimaries(G4Event *event, double current_simulation_time) {
    GamVSource::GeneratePrimaries(event, current_simulation_time);

    // generic ion cannot be created at initialization.
    // It must be created here, the first time
    if (fIsGenericIon) {
        auto ion_table = G4IonTable::GetIonTable();
        auto ion = ion_table->GetIon(fZ, fA);
        fSPS->SetParticleDefinition(ion);
        fIsGenericIon = false; // only the first time
    }

    fSPS->SetParticleTime(current_simulation_time);
    fSPS->GeneratePrimaryVertex(event);
    fN++;

    /*
    // DEBUG
    std::ostringstream oss;
    oss << event->GetEventID() << " "  << G4BestUnit(current_simulation_time, "Time")
     << " " << event->GetPrimaryVertex(0)->GetPosition() << std::endl;
    DDD(oss.str());
     */
}

void GamGenericSource::InitializeParticle(py::dict &user_info) {
    std::string pname = DictStr(user_info, "particle");
    // If the particle is an ion (name start with ion)
    if (pname.rfind("ion", 0) == 0) {
        InitializeIon(user_info);
        return;
    }
    // If the particle is not an ion
    fIsGenericIon = false;
    auto particle_table = G4ParticleTable::GetParticleTable();
    auto particle = particle_table->FindParticle(pname);
    if (particle == nullptr) {
        Fatal("Cannot find the particle '" + pname + "'.");
    }
    fSPS->SetParticleDefinition(particle);
}

void GamGenericSource::InitializeIon(py::dict &user_info) {
    auto u = py::dict(user_info["ion"]);
    fA = DictInt(u, "A");
    fZ = DictInt(u, "Z");
    fIsGenericIon = true;
}

void GamGenericSource::InitializePosition(py::dict user_info) {
    /* G4:
     * pos_types = ['Point', 'Beam', 'Plane', 'Surface', 'Volume']
     * shape_types = ['Square', 'Circle', 'Annulus', 'Ellipse', 'Rectangle',
                       'Sphere', 'Ellipsoid', 'Cylinder', 'Right', 'NULL']
    * New interface -> point box sphere disc (later: ellipse)
    * center rotation size radius
    */
    auto pos = fSPS->GetPosDist();
    auto pos_type = DictStr(user_info, "type");
    std::vector<std::string> l = {"sphere", "point", "box", "disc"};
    CheckIsIn(pos_type, l);
    auto center = DictVec(user_info, "center");
    if (pos_type == "point") {
        pos->SetPosDisType("Point");
    }
    if (pos_type == "box") {
        pos->SetPosDisType("Volume");
        pos->SetPosDisShape("Para");
        auto size = DictVec(user_info, "size") / 2.0;
        pos->SetHalfX(size[0]);
        pos->SetHalfY(size[1]);
        pos->SetHalfZ(size[2]);
    }
    if (pos_type == "sphere") {
        pos->SetPosDisType("Volume");
        pos->SetPosDisShape("Sphere");
        auto radius = DictFloat(user_info, "radius");
        pos->SetRadius(radius);
    }
    if (pos_type == "disc") {
        pos->SetPosDisType("Plane");
        pos->SetPosDisShape("Circle");
        auto radius = DictFloat(user_info, "radius");
        pos->SetRadius(radius);
    }
    // position center
    pos->SetCentreCoords(center);
    // rotation
    auto rotation = DictMatrix(user_info, "rotation");
    G4ThreeVector r1(*rotation.data(0, 0),
                     *rotation.data(0, 1),
                     *rotation.data(0, 2));
    G4ThreeVector r2(*rotation.data(1, 0),
                     *rotation.data(1, 1),
                     *rotation.data(1, 2));
    pos->SetPosRot1(r1);
    pos->SetPosRot2(r2);
}

void GamGenericSource::InitializeDirection(py::dict user_info) {
    /*
     * G4: iso, cos, beam  and user for isotropic, cosine-law, beam and user-defined
     *
     * New ones: iso, focus, direction
     * (Later: beam, user defined)
     */
    auto ang = fSPS->GetAngDist();
    auto ang_type = DictStr(user_info, "type");
    std::vector<std::string> l = {"iso", "momentum", "focused"};
    CheckIsIn(ang_type, l);
    if (ang_type == "iso") {
        ang->SetAngDistType("iso");
    }
    if (ang_type == "momentum") {
        ang->SetAngDistType("planar"); // FIXME really ??
        auto d = DictVec(user_info, "momentum");
        ang->SetParticleMomentumDirection(d);
    }
    if (ang_type == "focused") {
        ang->SetAngDistType("focused");
        auto f = DictVec(user_info, "focus_point");
        ang->SetFocusPoint(f);
    }
}

void GamGenericSource::InitializeEnergy(py::dict user_info) {
    /*
     * G4: Mono (mono-energetic), Lin (linear), Pow (power-law), Exp
     * (exponential), Gauss (gaussian), Brem (bremsstrahlung), BBody (black-body), Cdg
     * (cosmic diffuse gamma-ray), User (user-defined), Arb (arbitrary
     * point-wise), Epn (energy per nucleon).
     *
     * New interface: mono gauss // FIXME later 'user'
     *
     */
    auto ene = fSPS->GetEneDist();
    auto ene_type = DictStr(user_info, "type");
    std::vector<std::string> l = {"mono", "gauss"};
    CheckIsIn(ene_type, l);
    if (ene_type == "mono") {
        ene->SetEnergyDisType("Mono");
        auto e = DictFloat(user_info, "mono");
        ene->SetMonoEnergy(e);
    }
    if (ene_type == "gauss") {
        ene->SetEnergyDisType("Gauss");
        auto e = DictFloat(user_info, "mono");
        ene->SetMonoEnergy(e);
        auto g = DictFloat(user_info, "sigma_gauss");
        ene->SetBeamSigmaInE(g);
    }
}
