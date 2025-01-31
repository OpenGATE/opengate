#include "GateEmCalculatorActor.h"
#include "GateHelpersDict.h"

#include "G4Event.hh"
#include "G4IonTable.hh"
#include "G4MaterialTable.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"

#include "G4PhysicalConstants.hh"
#include "G4ProductionCutsTable.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"

/// Destructor
GateEmCalculatorActor::~GateEmCalculatorActor() {}
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
/// Construct
GateEmCalculatorActor::GateEmCalculatorActor(py::dict &user_info)
    : GateVActor(user_info, false) {

  // emcalc = new G4EmCalculator;
  // CalculateElectronicdEdX();
}

void GateEmCalculatorActor::InitializeUserInfo(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInfo(user_info);
  mPartName = DictGetStr(user_info, "particle_name");
  mIsGenericIon = DictGetBool(user_info, "is_ion");
  mParticleParameters = DictGetStr(user_info, "ion_params");
  mEnergies = DictGetVecDouble(user_info, "nominal_energies");
  mMaterial = DictGetStr(user_info, "material");
  mFilename = DictGetStr(user_info, "savefile_path");
}

void GateEmCalculatorActor::InitializeCpp() { emcalc = new G4EmCalculator; }

void GateEmCalculatorActor::BeginOfRunAction(const G4Run *) {
  //     std::cout<<"Begin of run!"<<std::endl;
  CalculateElectronicdEdX();
}

void GateEmCalculatorActor::SteppingAction(G4Step *step) {
  CalculateElectronicdEdX();
}

void GateEmCalculatorActor::CalculateElectronicdEdX() {
  double cut = DBL_MAX;
  double EmDEDX = 0;
  double I = 0;
  //   double eDensity=0;
  //   double radLength=0;
  //   double CSDArange = 0;
  double density;
  G4String material;
  const G4MaterialTable *matTbl = G4Material::GetMaterialTable();

  G4NistManager *manager = G4NistManager::Instance();
  G4Material *mat = manager->FindOrBuildMaterial(mMaterial);
  //   std::cout<<"\nMaterial: "<<mMaterial<<std::endl;
  density = mat->GetDensity();

  I = mat->GetIonisation()->GetMeanExcitationEnergy();

  const G4ParticleDefinition *gamma_definition =
      G4ParticleTable::GetParticleTable()->FindParticle("gamma");
  const G4ParticleDefinition *particle_definition =
      mIsGenericIon
          ? GetIonDefinition()
          : G4ParticleTable::GetParticleTable()->FindParticle(mPartName);

  // File stream
  std::ofstream os;
  os.open(mFilename.data());
  os << "# Output calculted for the following parameters:\n";
  os << "# Particle\t" << mPartName << " " << mParticleParameters
     << "\n"; // parameters are empty unless mPartName=GenericIon
  os << "# And for material: " << mMaterial << "\n";
  // labels
  os << "Energy [Mev/n]\t";
  os << "dEdX [MeV*cm2/g]\n";
  for (size_t j = 0; j < mEnergies.size(); j++) {
    double mass_number = particle_definition->GetAtomicMass();
    double mEnergy_n = mEnergies[j];
    double mEnergy = mEnergies[j] * mass_number;
    EmDEDX =
        emcalc->ComputeElectronicDEDX(mEnergy, particle_definition, mat, cut) *
        gram / (MeV * cm2 * density);
    //       NuclearDEDX = emcalc->ComputeNuclearDEDX(mEnergy,
    //       particle_definition, (*matTbl)[k]) / density; TotalDEDX =
    //       emcalc->ComputeTotalDEDX(mEnergy, particle_definition,
    //       (*matTbl)[k], cut) / density; CSDArange =
    //       emcalc->GetCSDARange(mEnergy, particle_definition, (*matTbl)[k]) /
    //       density; double MuMassCoeficient = 0.;

    //       std::cout<<"Energy: "<<mEnergy_n<<"  dEdX: "<<EmDEDX<<std::endl;
    os << mEnergy_n << "\t\t" << EmDEDX << "\n";
  }
  os.flush();
  os.close();
}

//-----------------------------------------------------------------------------
const G4ParticleDefinition *GateEmCalculatorActor::GetIonDefinition() {
  if (mPartName != "GenericIon") {
    // A bit late to do this here and now, but in the messenger the two options
    // may come in in any order, so it is not easy to check there. PencilBeam
    // and TPSPencilBeam have a simlar problem (not by coincidence, because I
    // tried to keep the options in the same style.)
    //       std::cout<<"Got ion parameters '" << mParticleParameters << "' but
    //       particle name " << mPartName << "!=GenericIon"<<std::endl;
  }
  int atomic_number = 0;
  int atomic_mass = 0;
  std::istringstream iss((const char *)mParticleParameters);
  iss >> atomic_number >> atomic_mass;
  //     std::cout<<"Got atomic number = " << atomic_number << " and atomic mass
  //     = " << atomic_mass << std::endl;
  const G4ParticleDefinition *p =
      G4IonTable::GetIonTable()->GetIon(atomic_number, atomic_mass);
  //     std::cout<<"particle name = " << p->GetParticleName()<< std::endl;

  return p;
}
