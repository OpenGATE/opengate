/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "G4IonTable.hh"
#include <G4UnitsTable.hh>
#include "GateGenericSource.h"
#include "GateHelpersDict.h"

GateGenericSource::GateGenericSource() : GateVSource() {
    fNumberOfGeneratedEvents = 0;
    fMaxN = 0;
    fActivity = 0;
    fIsGenericIon = false;
    fA = 0;
    fZ = 0;
    fE = 0;
    fInitConfine = false;
    fWeight = -1;
    fWeightSigma = -1;
    fHalfLife = -1;
    fLambda = -1;
}

GateGenericSource::~GateGenericSource() {
    // FIXME: we cannot really delete the fSPS here
    // because it has been created in a thread which
    // can be different from the thread that delete.
    // delete fSPS;
}

void GateGenericSource::CleanWorkerThread() {
    // Not used yet. Maybe later to clean local data in a thread.
}

void GateGenericSource::InitializeUserInfo(py::dict &user_info) {
    GateVSource::InitializeUserInfo(user_info);
    fSPS = new GateSingleParticleSource(fMother);

    // get user info about activity or nb of events
    fMaxN = DictGetInt(user_info, "n");
    fActivity = DictGetDouble(user_info, "activity");
    fInitialActivity = fActivity;

    // half life ?
    fHalfLife = DictGetDouble(user_info, "half_life");
    fLambda = log(2) / fHalfLife;

    // weight
    fWeight = DictGetDouble(user_info, "weight");
    fWeightSigma = DictGetDouble(user_info, "weight_sigma");

    // get the user info for the particle
    InitializeParticle(user_info);

    // position, direction, energy
    InitializePosition(user_info);
    InitializeDirection(user_info);
    InitializeEnergy(user_info);

    // FIXME todo polarization

    // init number of events
    fNumberOfGeneratedEvents = 0;
    fAASkippedParticles = 0;
}

void GateGenericSource::UpdateActivity(double time) {
    if (fHalfLife <= 0) return;
    fActivity = fInitialActivity * exp(-fLambda * (time - fStartTime));
}

double GateGenericSource::PrepareNextTime(double current_simulation_time) {
    // update the activity for half-life
    UpdateActivity(current_simulation_time);
    // check according to time
    if (fMaxN <= 0) {
        if (current_simulation_time < fStartTime) {
            return fStartTime;
        }
        if (current_simulation_time >= fEndTime) {
            fAASkippedParticles = fSPS->GetAASkippedParticles();
            return -1;
        }
        double next_time = current_simulation_time - log(G4UniformRand()) * (1.0 / fActivity);
        if (next_time >= fEndTime) {
            fAASkippedParticles = fSPS->GetAASkippedParticles();
        }
        return next_time;
    }
    // check according to t MaxN
    if (fNumberOfGeneratedEvents >= fMaxN) {
        fAASkippedParticles = fSPS->GetAASkippedParticles();
        return -1;
    }
    return fStartTime;
}

void GateGenericSource::PrepareNextRun() {
    // The following compute the global transformation from
    // the local volume (mother) to the world
    GateVSource::PrepareNextRun();
    // This global transformation is given to the SPS that will
    // generate particles in the correct coordinate system
    auto *pos = fSPS->GetPosDist();
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

void GateGenericSource::GeneratePrimaries(G4Event *event, double current_simulation_time) {
    // Generic ion cannot be created at initialization.
    // It must be created here, the first time we get there
    if (fIsGenericIon) {
        auto *ion_table = G4IonTable::GetIonTable();
        auto *ion = ion_table->GetIon(fZ, fA, fE);
        fSPS->SetParticleDefinition(ion);
        InitializeHalfTime(ion);
        fIsGenericIon = false; // only the first time
    }

    // Confine cannot be initialized at initialization (because need all volumes to be created)
    // It must be set here, the first time we get there
    if (fInitConfine) {
        auto *pos = fSPS->GetPosDist();
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

    fNumberOfGeneratedEvents++;
}

void GateGenericSource::InitializeParticle(py::dict &user_info) {
    std::string pname = DictGetStr(user_info, "particle");
    // If the particle is an ion (name start with ion)
    if (pname.rfind("ion", 0) == 0) {
        InitializeIon(user_info);
        return;
    }
    // If the particle is not an ion
    fIsGenericIon = false;
    auto *particle_table = G4ParticleTable::GetParticleTable();
    fParticleDefinition = particle_table->FindParticle(pname);
    if (fParticleDefinition == nullptr) {
        Fatal("Cannot find the particle '" + pname + "'.");
    }
    InitializeHalfTime(fParticleDefinition);
    fSPS->SetParticleDefinition(fParticleDefinition);
}

void GateGenericSource::InitializeIon(py::dict &user_info) {
    auto u = py::dict(user_info["ion"]);
    fA = DictGetInt(u, "A");
    fZ = DictGetInt(u, "Z");
    fE = DictGetDouble(u, "E");
    fIsGenericIon = true;
}

void GateGenericSource::InitializePosition(py::dict puser_info) {
    /* G4:
     * pos_types = ['Point', 'Beam', 'Plane', 'Surface', 'Volume']
     * shape_types = ['Square', 'Circle', 'Annulus', 'Ellipse', 'Rectangle',
                       'Sphere', 'Ellipsoid', 'Cylinder', 'Right', 'NULL']
    * New interface -> point box sphere disc (later: ellipse)
    * translation rotation size radius
    */
    auto user_info = py::dict(puser_info["position"]);
    auto *pos = fSPS->GetPosDist();
    auto pos_type = DictGetStr(user_info, "type");
    std::vector<std::string> l = {"sphere", "point", "box", "disc", "cylinder"};
    CheckIsIn(pos_type, l);
    auto translation = DictGetG4ThreeVector(user_info, "translation");
    if (pos_type == "point") {
        pos->SetPosDisType("Point");
    }
    if (pos_type == "box") {
        pos->SetPosDisType("Volume");
        pos->SetPosDisShape("Para");
        auto size = DictGetG4ThreeVector(user_info, "size") / 2.0;
        pos->SetHalfX(size[0]);
        pos->SetHalfY(size[1]);
        pos->SetHalfZ(size[2]);
    }
    if (pos_type == "sphere") {
        pos->SetPosDisType("Volume");
        pos->SetPosDisShape("Sphere");
    }
    if (pos_type == "disc") {
        pos->SetPosDisType("Beam"); // FIXME ?  Cannot be plane
        pos->SetPosDisShape("Circle");
    }
    if (pos_type == "cylinder") {
        pos->SetPosDisType("Volume");
        pos->SetPosDisShape("Cylinder");
        auto dz = DictGetDouble(user_info, "dz");
        pos->SetHalfZ(dz / 2.0);
    }

    // radius for sphere, disc, cylinder
    auto radius = DictGetDouble(user_info, "radius");
    pos->SetRadius(radius);

    // gaussian sigma for disc
    auto sx = DictGetDouble(user_info, "sigma_x");
    pos->SetBeamSigmaInX(sx);
    auto sy = DictGetDouble(user_info, "sigma_y");
    pos->SetBeamSigmaInY(sy);

    // rotation
    auto rotation = DictGetMatrix(user_info, "rotation");

    // save local translation and rotation (will be used in SetOrientationAccordingToMotherVolume)
    fLocalTranslation = translation;
    fLocalRotation = ConvertToG4RotationMatrix(rotation);//G4RotationMatrix(colX, colY, colZ);

    // confine to a volume ?
    if (user_info.contains("confine")) {
        auto v = DictGetStr(user_info, "confine");
        if (v != "None") {
            fConfineVolume = v;
            fInitConfine = true;
        }
    }
}

void GateGenericSource::InitializeDirection(py::dict puser_info) {
    /*
     * G4: iso, cos, beam  and user for isotropic, cosine-law, beam and user-defined
     *
     * New ones: iso, focus, direction
     * (Later: beam, user defined)
     */
    auto user_info = py::dict(puser_info["direction"]);
    auto *ang = fSPS->GetAngDist();
    auto ang_type = DictGetStr(user_info, "type");
    std::vector<std::string> l = {"iso", "momentum", "focused", "beam2d"}; // FIXME check on py side ?
    CheckIsIn(ang_type, l);
    if (ang_type == "iso") {
        ang->SetAngDistType("iso");
    }
    if (ang_type == "momentum") {
        ang->SetAngDistType("planar"); // FIXME really ??
        auto d = DictGetG4ThreeVector(user_info, "momentum");
        ang->SetParticleMomentumDirection(d);
    }
    if (ang_type == "focused") {
        ang->SetAngDistType("focused");
        auto f = DictGetG4ThreeVector(user_info, "focus_point");
        ang->SetFocusPoint(f);
    }
    if (ang_type == "beam2d") {
        ang->SetAngDistType("beam2d");
        auto sigma = DictGetVecDouble(user_info, "sigma");
        ang->SetBeamSigmaInAngX(sigma[0]);
        ang->SetBeamSigmaInAngY(sigma[1]);
    }

    // set the angle acceptance volume if needed
    auto d = py::dict(puser_info["direction"]);
    auto dd = py::dict(d["acceptance_angle"]);
    fSPS->SetAcceptanceAngleParam(dd);
}

void GateGenericSource::InitializeEnergy(py::dict puser_info) {
    /*
     * G4: Mono (mono-energetic), Lin (linear), Pow (power-law), Exp
     * (exponential), Gauss (gaussian), Brem (bremsstrahlung), BBody (black-body), Cdg
     * (cosmic diffuse gamma-ray), User (user-defined), Arb (arbitrary
     * point-wise), Epn (energy per nucleon).
     *
     * New interface: mono gauss // later 'user'
     *
     */
    auto user_info = py::dict(puser_info["energy"]);
    auto *ene = fSPS->GetEneDist();
    auto ene_type = DictGetStr(user_info, "type");
    auto is_cdf = DictGetBool(user_info, "is_cdf");

    // Get it
    if (ene_type == "mono") {
        ene->SetEnergyDisType("Mono");
        auto e = DictGetDouble(user_info, "mono");
        ene->SetMonoEnergy(e);
    }

    if (ene_type == "gauss") {
        ene->SetEnergyDisType("Gauss");
        auto e = DictGetDouble(user_info, "mono");
        ene->SetMonoEnergy(e);
        auto g = DictGetDouble(user_info, "sigma_gauss");
        ene->SetBeamSigmaInE(g);
    }

    if (ene_type == "range") {
        ene->SetEnergyDisType("range");
        auto emin = DictGetDouble(user_info, "min_energy");
        auto emax = DictGetDouble(user_info, "max_energy");
        ene->SetEmin(emin);
        ene->SetEmax(emax);
    }

    if (ene_type == "spectrum") {
        ene->SetEnergyDisType("User");
        auto w = DictGetVecDouble(user_info, "spectrum_weight");
        auto e = DictGetVecDouble(user_info, "spectrum_energy");
        auto total = 0.0;
        for (unsigned long i = 0; i < w.size(); i++) {
            G4ThreeVector x(e[i], w[i], 0);
            ene->UserEnergyHisto(x);
            total += w[i];
        }
        // Modify the activity according to the total weight
        fActivity = fActivity * total;
        fInitialActivity = fActivity;
    }

    if (ene_type == "F18_analytic") {
        ene->SetEnergyDisType("F18_analytic");
    }

    if (ene_type == "O15_analytic") {
        ene->SetEnergyDisType("O15_analytic");
    }

    if (ene_type == "C11_analytic") {
        ene->SetEnergyDisType("C11_analytic");
    }

    if (is_cdf) {
        ene->SetEnergyDisType("CDF");
        ene->fEnergyCDF = fEnergyCDF;
        ene->fProbabilityCDF = fProbabilityCDF;
        // CDF should be set from py side
    }
}

void GateGenericSource::InitializeHalfTime(G4ParticleDefinition *p) {
    // We force the lifetime to zero because this is managed by a user option
    p->SetPDGLifeTime(0);
    // Special case to retrieve the PDGLife Time
    // However, for F18, the LifeTime is 9501.88 not 6586.26 ?
    // So we don't use this for the moment
    if (fHalfLife == -2) {
        fHalfLife = p->GetPDGLifeTime();
        fLambda = log(2) / fHalfLife;
    }
}
