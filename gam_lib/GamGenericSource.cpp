/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "G4IonTable.hh"
#include "GamGenericSource.h"
#include "GamDictHelpers.h"

GamGenericSource::GamGenericSource() : GamVSource() {
    fN = 0;
    fMaxN = 0;
    fActivity = 0;
    fIsGenericIon = false;
    fA = 0;
    fZ = 0;
    fE = 0;
    fInitConfine = false;
    fWeight = -1;
    fWeightSigma = -1;
}

GamGenericSource::~GamGenericSource() {
    // FIXME: we cannot really delete the fSPS here
    // because it has been created in a thread which
    // can be different from the thread that delete.
    // delete fSPS;
}

void GamGenericSource::CleanWorkerThread() {
    // Not used yet. Maybe later to clean local data in a thread.
}

void GamGenericSource::InitializeUserInfo(py::dict &user_info) {
    GamVSource::InitializeUserInfo(user_info);
    fSPS = new GamSingleParticleSource();

    // get the user info for the particle
    InitializeParticle(user_info);

    // get user info about activity or nb of events
    // FIXME check here if not both
    fMaxN = DictInt(user_info, "n");
    fActivity = DictFloat(user_info, "activity");
    fInitialActivity = fActivity;
    fHalfLife = DictFloat(user_info, "half_life");
    fLambda = log(2) / fHalfLife;
    fWeight = DictFloat(user_info, "weight");
    fWeightSigma = DictFloat(user_info, "weight_sigma");

    // position, direction, energy
    InitializePosition(user_info);
    InitializeDirection(user_info);
    InitializeEnergy(user_info);

    // FIXME todo polarization

    // FIXME confine

    // init number of events
    fN = 0;
}

void GamGenericSource::UpdateActivity(double time) {
    if (fHalfLife <= 0) return;
    fActivity = fInitialActivity * exp(-fLambda * (time - fStartTime));
}

double GamGenericSource::PrepareNextTime(double current_simulation_time) {
    // update the activity for half-life
    UpdateActivity(current_simulation_time);
    // check according to time
    if (fMaxN <= 0) {
        if (current_simulation_time < fStartTime) {
            return fStartTime;
        }
        if (current_simulation_time >= fEndTime) {
            return -1;
        }
        double next_time = current_simulation_time - log(G4UniformRand()) * (1.0 / fActivity);
        return next_time;
    }
    // check according to t MaxN
    if (fN >= fMaxN) return -1;
    return fStartTime;
}

void GamGenericSource::PrepareNextRun() {
    GamVSource::PrepareNextRun();
    auto pos = fSPS->GetPosDist();
    pos->SetCentreCoords(fGlobalTranslation);
    // orientation according to mother volume
    auto rotation = fGlobalRotation;
    G4ThreeVector r1(rotation(0, 0),
                     rotation(0, 1),
                     rotation(0, 2));
    G4ThreeVector r2(rotation(1, 0),
                     rotation(1, 1),
                     rotation(1, 2));
    pos->SetPosRot1(r1);
    pos->SetPosRot2(r2);
}

void GamGenericSource::GeneratePrimaries(G4Event *event, double current_simulation_time) {
    // Generic ion cannot be created at initialization.
    // It must be created here, the first time we get there
    if (fIsGenericIon) {
        auto ion_table = G4IonTable::GetIonTable();
        auto ion = ion_table->GetIon(fZ, fA, fE);
        fSPS->SetParticleDefinition(ion);
        fIsGenericIon = false; // only the first time
    }

    // Confine cannot be initialized at initialization (because need all volumes to be created)
    // It must be set here, the first time we get there
    if (fInitConfine) {
        auto pos = fSPS->GetPosDist();
        pos->ConfineSourceToVolume(fConfineVolume);
        fInitConfine = false;
    }

    // sample the particle properties with SingleParticleSource
    fSPS->SetParticleTime(current_simulation_time);
    fSPS->GeneratePrimaryVertex(event);

    // weight ?
    if (fWeight > 0) {
        if (fWeightSigma < 0) {
            for (auto i = 0; i < event->GetNumberOfPrimaryVertex(); i++) {
                event->GetPrimaryVertex(i)->SetWeight(fWeight);
            }
        } else { // weight is Gaussian
            for (auto i = 0; i < event->GetNumberOfPrimaryVertex(); i++) {
                double w = G4RandGauss::shoot(fWeight, fWeightSigma);
                event->GetPrimaryVertex(i)->SetWeight(w);
            }
        }
    }

    fN++;

    /*
    // DEBUG
    std::ostringstream oss;
    oss << event->GetEventID() << " "
        << G4BestUnit(current_simulation_time, "Time")
        << " " << event->GetPrimaryVertex(0)->GetPosition()
        << " " << G4BestUnit(event->GetPrimaryVertex(0)->GetPrimary()->GetKineticEnergy(), "Energy")
        << std::endl;
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
    fE = DictFloat(u, "E");
    fIsGenericIon = true;
}

void GamGenericSource::InitializePosition(py::dict puser_info) {
    /* G4:
     * pos_types = ['Point', 'Beam', 'Plane', 'Surface', 'Volume']
     * shape_types = ['Square', 'Circle', 'Annulus', 'Ellipse', 'Rectangle',
                       'Sphere', 'Ellipsoid', 'Cylinder', 'Right', 'NULL']
    * New interface -> point box sphere disc (later: ellipse)
    * translation rotation size radius
    */
    auto user_info = py::dict(puser_info["position"]);
    auto pos = fSPS->GetPosDist();
    auto pos_type = DictStr(user_info, "type");
    std::vector<std::string> l = {"sphere", "point", "box", "disc"};
    CheckIsIn(pos_type, l);
    auto translation = DictVec(user_info, "translation");
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
        pos->SetPosDisType("Beam"); // FIXME ?  Cannot be plane
        pos->SetPosDisShape("Circle");
        auto radius = DictFloat(user_info, "radius");
        pos->SetRadius(radius);
    }

    // rotation
    auto rotation = DictMatrix(user_info, "rotation");

    // save local translation and rotation (will be used in SetOrientationAccordingToMotherVolume)
    fLocalTranslation = translation;
    G4ThreeVector colX(*rotation.data(0, 0), *rotation.data(0, 1), *rotation.data(0, 2));
    G4ThreeVector colY(*rotation.data(1, 0), *rotation.data(1, 1), *rotation.data(1, 2));
    G4ThreeVector colZ(*rotation.data(2, 0), *rotation.data(2, 1), *rotation.data(2, 2));
    fLocalRotation = G4RotationMatrix(colX, colY, colZ);

    // confine to a volume ?
    if (user_info.contains("confine")) {
        auto v = DictStr(user_info, "confine");
        if (v != "None") {
            fConfineVolume = v;
            fInitConfine = true;
        }
    }
}

void GamGenericSource::InitializeDirection(py::dict puser_info) {
    /*
     * G4: iso, cos, beam  and user for isotropic, cosine-law, beam and user-defined
     *
     * New ones: iso, focus, direction
     * (Later: beam, user defined)
     */
    auto user_info = py::dict(puser_info["direction"]);
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

void GamGenericSource::InitializeEnergy(py::dict puser_info) {
    /*
     * G4: Mono (mono-energetic), Lin (linear), Pow (power-law), Exp
     * (exponential), Gauss (gaussian), Brem (bremsstrahlung), BBody (black-body), Cdg
     * (cosmic diffuse gamma-ray), User (user-defined), Arb (arbitrary
     * point-wise), Epn (energy per nucleon).
     *
     * New interface: mono gauss // FIXME later 'user'
     *
     */
    auto user_info = py::dict(puser_info["energy"]);
    auto ene = fSPS->GetEneDist();
    auto ene_type = DictStr(user_info, "type");
    // Check the type of ene is known
    std::vector<std::string> l = {"mono", "gauss", "F18"};
    CheckIsIn(ene_type, l);
    // Get it
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
    if (ene_type == "F18") {
        ene->SetEnergyDisType("Fluor18");
    }
}
