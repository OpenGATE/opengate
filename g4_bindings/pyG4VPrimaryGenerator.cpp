/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VPrimaryGenerator.hh"
#include "G4Event.hh"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// Needed helper class because of the pure virtual method
class PyG4VPrimaryGenerator : public G4VPrimaryGenerator {
public:
    // Inherit the constructors
    using G4VPrimaryGenerator::G4VPrimaryGenerator;

    // Trampoline (need one for each virtual function)
    void GeneratePrimaryVertex(G4Event *evt) override {
        std::cout << "@@@@PyG4VPrimaryGenerator GeneratePrimaryVertex " << std::endl;
        PYBIND11_OVERLOAD_PURE(void,
                               G4VPrimaryGenerator,
                               GeneratePrimaryVertex,
                               evt);
    }

};

void init_G4VPrimaryGenerator(py::module &m) {
    py::class_<G4VPrimaryGenerator, PyG4VPrimaryGenerator>(m, "G4VPrimaryGenerator")

            .def("GeneratePrimaryVertex", &G4VPrimaryGenerator::GeneratePrimaryVertex)

        /*
          class G4VPrimaryGenerator
          {
          public: // with description
          // static service method for checking a point is included in the (current) world
          static G4bool CheckVertexInsideWorld(const G4ThreeVector& pos);

          public: // with description
          // Constructor and destrucot of this base class
          G4VPrimaryGenerator();
          virtual ~G4VPrimaryGenerator();

          // Pure virtual method which a concrete class derived from this base class must
          // have a concrete implementation
          virtual void GeneratePrimaryVertex(G4Event* evt) = 0;

          protected:
          G4ThreeVector         particle_position;
          G4double              particle_time;

          public:
          G4ThreeVector GetParticlePosition()
          { return particle_position; }
          G4double GetParticleTime()
          { return particle_time; }
          void SetParticlePosition(G4ThreeVector aPosition)
          { particle_position = aPosition; }
          void SetParticleTime(G4double aTime)
          { particle_time = aTime; }
          };
        */
            ;
}
