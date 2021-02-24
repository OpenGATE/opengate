/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Version.hh"
#include "G4ParticleTable.hh"
#include "G4ParticleDefinition.hh"
#include "G4String.hh"

#include "G4LeptonConstructor.hh"
#include "G4BosonConstructor.hh"
#include "G4MesonConstructor.hh"
#include "G4BaryonConstructor.hh"
#include "G4ShortLivedConstructor.hh"
#include "G4IonConstructor.hh"

void init_G4ParticleTable(py::module &m) {

    /*
      namespace pyG4ParticleTable {

      // contains...
      G4bool(G4ParticleTable::*f1_contains)(const G4ParticleDefinition*) const
      = &G4ParticleTable::contains;

      G4bool(G4ParticleTable::*f2_contains)(const G4String&) const
      = &G4ParticleTable::contains;

      // FindParticle...
      G4ParticleDefinition*(G4ParticleTable::*f1_FindParticle)(G4int)
      = &G4ParticleTable::FindParticle;

      G4ParticleDefinition*(G4ParticleTable::*f2_FindParticle)(const G4String&)
      = &G4ParticleTable::FindParticle;

      G4ParticleDefinition*(G4ParticleTable::*f3_FindParticle)(
      const G4ParticleDefinition*)= &G4ParticleTable::FindParticle;

      // FindAntiParticle...
      G4ParticleDefinition*(G4ParticleTable::*f1_FindAntiParticle)(G4int)
      = &G4ParticleTable::FindAntiParticle;

      G4ParticleDefinition*(G4ParticleTable::*f2_FindAntiParticle)(const G4String&)
      = &G4ParticleTable::FindAntiParticle;

      G4ParticleDefinition*(G4ParticleTable::*f3_FindAntiParticle)(
      const G4ParticleDefinition*)= &G4ParticleTable::FindAntiParticle;

      // DumpTable
      BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(f_DumpTable, DumpTable, 0, 1)


      // --------------------------------------------------------------------
      // GetParticleList (returning python list)

      list GetParticleList(G4ParticleTable* particleTable)
      {
      list particleList;
      G4ParticleTable::G4PTblDicIterator*
      theParticleIterator= particleTable-> GetIterator();
      theParticleIterator-> reset();
      while( (*theParticleIterator)() ){
      G4ParticleDefinition* particle= theParticleIterator-> value();
      particleList.append(&particle);
      }

      return particleList;
      }

      }

      using namespace pyG4ParticleTable;
    */


    //  py::class_<G4ParticleTable, std::unique_ptr<G4ParticleTable, py::nodelete>>(m, "G4ParticleTable")
    py::class_<G4ParticleTable,
        std::unique_ptr<G4ParticleTable, py::nodelete>>(m, "G4ParticleTable")

        .def("GetParticleTable", &G4ParticleTable::GetParticleTable,
             py::return_value_policy::reference)

        .def("CreateAllParticles",
             [](const G4ParticleTable &) {
                 // Create all particles
                 // std::cout << "Create All Particles" << std::endl;
                 G4LeptonConstructor::ConstructParticle();
                 G4BosonConstructor::ConstructParticle();
                 G4MesonConstructor::ConstructParticle();
                 G4BaryonConstructor::ConstructParticle();
                 G4ShortLivedConstructor::ConstructParticle();
                 G4IonConstructor::ConstructParticle();
                 // std::cout << "END create All Particles" << std::endl;
             })

            //.def("contains",          f1_contains)
            //.def("contains",          f2_contains)

        .def("entries", &G4ParticleTable::entries)
        .def("size", &G4ParticleTable::size)

        .def("GetParticle", &G4ParticleTable::GetParticle, py::return_value_policy::reference)
        .def("GetParticleName", &G4ParticleTable::GetParticleName, py::return_value_policy::copy)

        .def("FindParticle",
            //py::overload_cast<G4String>(&G4ParticleTable::FindParticle))//,
             (G4ParticleDefinition *(G4ParticleTable::*)(const G4String &))
                 &G4ParticleTable::FindParticle,
             py::return_value_policy::reference,
             py::arg("particle_name"))

        .def("FindParticle",
            //py::overload_cast<G4String>(&G4ParticleTable::FindParticle))//,
             (G4ParticleDefinition *(G4ParticleTable::*)(G4int))
                 &G4ParticleTable::FindParticle,
             py::return_value_policy::reference,
             py::arg("PDGEncoding"))

        .def("FindParticle",
            //py::overload_cast<G4String>(&G4ParticleTable::FindParticle))//,
             (G4ParticleDefinition *(G4ParticleTable::*)(const G4ParticleDefinition *))
                 &G4ParticleTable::FindParticle,
             py::return_value_policy::reference,
             py::arg("particle"))


            /*
              .def("FindParticle",      f1_FindParticle,
              return_value_policy<reference_existing_object>())
              .def("FindParticle",      f2_FindParticle,
              return_value_policy<reference_existing_object>())
              .def("FindParticle",      f3_FindParticle,
              return_value_policy<reference_existing_object>())
              .def("FindAntiParticle",  f1_FindAntiParticle,
              return_value_policy<reference_existing_object>())
              .def("FindAntiParticle",  f2_FindAntiParticle,
              return_value_policy<reference_existing_object>())
              .def("FindAntiParticle",  f3_FindAntiParticle,
              return_value_policy<reference_existing_object>())
            */

        .def("DumpTable", &G4ParticleTable::DumpTable) //, f_DumpTable())

            //.def("GetIonTable",     &G4ParticleTable::GetIonTable,
            //...)
            //.def("GetShortLivedTable", &G4ParticleTable::GetShortLivedTable,
            //...)

        .def("SetVerboseLevel", &G4ParticleTable::SetVerboseLevel)
        .def("GetVerboseLevel", &G4ParticleTable::GetVerboseLevel)
        .def("SetReadiness", &G4ParticleTable::SetReadiness)
        .def("GetReadiness", &G4ParticleTable::GetReadiness)

        // additionals
        //.def("GetParticleList",   GetParticleList)
        ;

}
