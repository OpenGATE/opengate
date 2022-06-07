/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamGANSource_h
#define GamGANSource_h

#include <pybind11/stl.h>
#include "GamGenericSource.h"
#include "GamSingleParticleSource.h"
#include "GamSPSVoxelsPosDistribution.h"

namespace py = pybind11;

class GamGANSource : public GamGenericSource {

public:

    // signature of the callback function in Python that will generate particles info
    using ParticleGeneratorType = std::function<void(GamGANSource *)>;

    GamGANSource();

    virtual ~GamGANSource();

    void InitializeUserInfo(py::dict &user_info) override;

    void PrepareNextRun() override;

    void GeneratePrimaries(G4Event *event, double current_simulation_time) override;

    void SetGeneratorFunction(ParticleGeneratorType &f);

    void GetParticlesInformation();

    std::vector<double> fPositionX;
    std::vector<double> fPositionY;
    std::vector<double> fPositionZ;

    std::vector<double> fDirectionX;
    std::vector<double> fDirectionY;
    std::vector<double> fDirectionZ;

    std::vector<double> fEnergy;
    bool fUseWeight;
    std::vector<double> fWeight;
    bool fUseTime;
    bool fUseTimeRelative;
    std::vector<double> fTime;

    ParticleGeneratorType fGenerator;
    size_t fCurrentIndex;
    double fCharge;
    double fMass;
    int fNumberOfNegativeEnergy;

};

#endif // GamGANSource_h
