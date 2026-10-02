/* AMF port from 624a6f863be8b90a2669e07b760efe07a1351dcb.
   Copyright (C): OpenGATE Collaboration. LGPL; see LICENSE.md. */
#ifndef GateAMFActor_h
#define GateAMFActor_h

#include "GateVActor.h"
#include "GateAMFAccumulator.h"
#include "GateHelpersImage.h"
#include <G4Cache.hh>
#include "G4SystemOfUnits.hh"
#include "itkImage.h"
#include "itkVectorImage.h"
#include <memory>
#include <mutex>
#include <vector>
#include <cmath>
#include <pybind11/stl.h>

class MicrodosimetricCalculator;

/** Score eligible ion steps with worker-local AMF data and master-only images. */
class GateAMFActor : public GateVActor {
public:
  using Image3DType = itk::Image<double, 3>;
  using ImageVectorType = itk::VectorImage<double, 3>;
  using VectorPixelType = ImageVectorType::PixelType;
  /** Register step/event/worker callbacks without allocating scoring images. */
  explicit GateAMFActor(py::dict &user_info);
  /** Release the owned calculator and worker data. */
  ~GateAMFActor() override;
  /** Read grid settings, load coefficients and prepare the worker model. */
  void InitializeUserInfo(py::dict &user_info) override;
  /** Validate dimensions, allocate enabled images and freeze configuration. */
  void InitializeCpp() override;
  /** Attach images and cache voxel volume for the sole supported run (id 0). */
  void BeginOfRunActionMasterThread(int run_id) override;
  /** Merge finished workers, normalize once and copy results to images; return 0. */
  int EndOfRunActionMasterThread(int run_id) override;
  /** Allocate and register this worker's calculator scratch and raw sums. */
  void BeginOfRunAction(const G4Run *) override;
  /** Mark this worker complete before master reduction. */
  void EndOfRunAction(const G4Run *) override;
  /** Count an event on the current worker, including events without scored hits. */
  void BeginOfEventAction(const G4Event *) override;
  /** Accumulate dose, spectrum and enabled moments for an eligible ion step. */
  void SteppingAction(G4Step *step) override;
  /** Set the physical placement name used when attaching images. */
  void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }
  /** Return the physical placement name used by the scoring grid. */
  std::string GetPhysicalVolumeName() const { return fPhysicalVolumeName; }
  /** Select the hit point and fill its image index; use the index only if inside. */
  void GetVoxelPosition(G4Step *, G4ThreeVector &, bool &, Image3DType::IndexType &) const;
  /** Return weighted deposited energy divided by pre-step voxel mass, in Gy. */
  double getDose(G4Step *) const;
  /** Return Geant4 total DEDX at mean step energy in keV/um, using worker scratch. */
  double GetStoppingPower(G4Step *);
  /** Return the 400 arithmetic lineal-energy bin midpoints in keV/um. */
  std::vector<double> GetHistogramLabels() const;
  /** Return whether the 400-component spectrum image is enabled. */
  bool GetMicrodosimetricSpectraFlag() const { return fMicrodosimetricSpectra; }
  /** Enable spectrum storage before initialization; scalar kernels are unaffected. */
  void SetMicrodosimetricSpectraFlag(bool b) { CheckConfigurationMutable(); fMicrodosimetricSpectra = b; }
  /** Return whether dose-mean lineal energy is enabled. */
  bool GetDoseAveragedLinealEnergyFlag() const { return fdoseAveragedLinealEnergy; }
  /** Enable the dose-mean lineal-energy numerator before initialization. */
  void SetDoseAveragedLinealEnergyFlag(bool b) { CheckConfigurationMutable(); fdoseAveragedLinealEnergy = b; }
  /** Return whether the saturation-corrected lineal-energy output is enabled. */
  bool GetDoseAveragedLinealEnergySaturationCorrectedFlag() const { return fdoseAveragedLinealEnergySaturationCorrected; }
  /** Enable the saturation-corrected numerator before initialization. */
  void SetDoseAveragedLinealEnergySaturationCorrectedFlag(bool b) { CheckConfigurationMutable(); fdoseAveragedLinealEnergySaturationCorrected = b; }
  /** Enable the MCF MKM alpha numerator before initialization. */
  void SetAlphaMCFMKMFlag(bool b) { CheckConfigurationMutable(); fAlphaMCFMKMFlag = b; }
  /** Enable the MCF MKM square-root beta numerator before initialization. */
  void SetBetaMCFMKMFlag(bool b) { CheckConfigurationMutable(); fBetaMCFMKMFlag = b; }
  /** Convert a radius in Geant4 length units to um for target and biology. */
  void SetDomainRadius(double x) { CheckConfigurationMutable(); fdomainRadiusInUm = x / CLHEP::um; }
  /** Convert the biological nuclear radius from Geant4 length units to um. */
  void SetNucleusRadius(double x) { CheckConfigurationMutable(); fNucleusRadiusInUm = x / CLHEP::um; }
  /** Convert reference beta from Geant4 inverse-dose-squared units to Gy^-2. */
  void SetBetaRef(double x) { CheckConfigurationMutable(); fBetaRefinGyminus2 = x * CLHEP::gray * CLHEP::gray; }
  /** Store reference alpha in Gy^-1; retained for compatibility, unused by scoring. */
  void SetAlphaRef(double x) { CheckConfigurationMutable(); fAlphaRefinGyminus1 = x * CLHEP::gray; }
  /** Convert biological alpha0 from Geant4 inverse-dose units to Gy^-1. */
  void SetAlphaNot(double x) { CheckConfigurationMutable(); fAlphaNotinGyminus1 = x * CLHEP::gray; }

  Image3DType::Pointer cpp_amf_dose_image;
  ImageVectorType::Pointer cpp_amf_microdosimetric_spectra;
  Image3DType::Pointer cpp_amf_dose_averaged_lineal_energy_saturation_corrected;
  Image3DType::Pointer cpp_amf_dose_averaged_lineal_energy;
  Image3DType::Pointer cpp_amf_alpha_mcfmkm_image;
  Image3DType::Pointer cpp_amf_beta_mcfmkm_image;
  int NbOfEvent = 0;
  std::string fPhysicalVolumeName;
private:
  /** Reject changes to calculator or output settings after image allocation. */
  void CheckConfigurationMutable() const {
    if (fInitialized) throw std::runtime_error("AMF: configuration cannot change after initialization");
  }
  static constexpr int nybin = 400;
  double fVoxelVolume = 0;
  std::string fHitType;
  G4ThreeVector fImageSize, fImageSpacing, fTranslation;
  G4RotationMatrix fImageRotation;
  double fdomainRadiusInUm = 0.3, fNucleusRadiusInUm = 4.5;
  double fBetaRefinGyminus2 = 0.0615, fAlphaRefinGyminus1 = 0.217, fAlphaNotinGyminus1 = 0.117;
  bool fMicrodosimetricSpectra = true;
  bool fdoseAveragedLinealEnergy = false, fdoseAveragedLinealEnergySaturationCorrected = false;
  bool fAlphaMCFMKMFlag = true, fBetaMCFMKMFlag = true;
  bool fFinalized = false;
  bool fInitialized = false, fStarted = false;
  std::array<bool, 4> fMomentFlags{};
  struct WorkerData;
  // Actor owns workers; G4Cache contains non-owning pointers. Registration is
  // synchronized once per worker. Only the master reads workers after beamOn.
  G4Cache<WorkerData *> fWorkerCache;
  std::vector<std::unique_ptr<WorkerData>> fWorkers;
  std::mutex fRegistrationMutex;
  std::unique_ptr<MicrodosimetricCalculator> calculator;
};

/** Evaluate ion AMF distributions with shared immutable fits and private scratch. */
class MicrodosimetricCalculator {
  private:
    using ImageVectorType = itk::VectorImage<double, 3>;
    using VectorPixelType = ImageVectorType::PixelType;

    // Member variables
    size_t nybin{};
    double CelDiam{};
    double fDomainRadius{};
    double fNucleusRadius{};
    double fBetaRef{};
    int iunit{};
    int mparased{};
    double factor{};
    std::string fTSEDfilename;
    std::vector<double> yhig, yfy, ydy;
    std::vector<double> ymid, ywid, eventmid, Z;
    using Model = std::vector<std::vector<double>>;
    std::shared_ptr<const Model> IonData;
    std::vector<double> histo_x_labels;

    double Apara[9];  // Fixed size based on mparased constant

    double ypower{};            // initialized in initialize()
    static constexpr double ystep = 0.02;
    double unitconv{};
    double binsperDecade{};
    double y0{};

    // Option: indicate we must calculate lineal energy spectra
    bool fMicrodosimetricSpectra=true;
    // Option: indicate we must calculate mean lineal energy
    bool fdoseAveragedLinealEnergySaturationCorrected=true;
    // Option: indicate we must calculate dose-averaged lineal energy
    bool fdoseAveragedLinealEnergy=true;

    // Constants (class-level)
    static constexpr int ROWS = 576;
    static constexpr int COLS = 9;
    const std::vector<double> eincion = {1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0, 50.0, 100.0, 300.0, 999.0};
	  const std::vector<double> cdiamion = {0.003, 0.01, 0.03, 0.1, 0.2, 0.3, 0.5, 1.0};
	  const std::vector<int> izion = {1, 2, 6, 10, 14, 26};



    struct IonParamCombo {
          double weight;      // Rp * Re * Rc
          double A0, A1, A2, A3, A4, A5, A6, A7, A8;
          double cst1;        // depev / A8  (or 0 if depev == 0)
          double firstPref;   // 2.0 / pow(cst1 * A2, 2)  when depev != 0
          double logBase7;    // std::log((A7 - 1.0) / A7) for third term
      };


    /** Precompute logarithmic bin geometry, unit conversion and saturation weights. */
    void initialize();

    /** Cache nonzero interpolation corners and return their count (1..8).
     * depev is in eV; lower grid indices are one-based. Fractions weight the
     * upper corner on each axis. weightedA8 receives the interpolated w-value.
     */
    inline int buildIonParamCombos(
          double depev, int ic1, int ie1, int ip1, double ratioc, double ratioe, double ratiop,
          IonParamCombo combos[8],          // output
          double& weightedA8                // output: Σ weight * A8
      ) const;

    /** Evaluate the interpolated ionization-count density at x using cached corners.
     * Preserve the legacy zero-deposit branch, exponent caps and tail cutoff.
     */
    inline double sedmeanFast(double x, bool depevZero, const IonParamCombo* combos, int nCombos) const;

    /** Find clamped one-based lower indices and upper-corner interpolation fractions.
     * Diameter is in um and energy in MeV/u; their weights are logarithmic,
     * while atomic-number interpolation is linear.
     */
    void getAparaion(const double& CelDiam, const double& energyPerNucleon, const int& izz,
                     double& ratioc, double& ratioe, double& ratiop, int& ic1, int& ie1, int& ip1);

    /** Evaluate the legacy eight-corner density and write interpolated A8 to Apara.
     * Other Apara entries retain the last corner's coefficients; x is an
     * ionization count and depev is the deposit proxy in eV.
     */
    inline double sedmean(double x, double depev, int ic1, int ie1, int ip1,
                   double ratioc, double ratioe, double ratiop, double Apara[]);
    /** Evaluate one legacy three-component fit with exponent caps and tail cutoff.
     * x is an ionization count, depev is in eV and Apara has nine coefficients.
     */
    inline double sedfunc(double x, double depev, const double Apara[], size_t size);

    public:

    // Pixel type alias exposed (if callers need it)
    using PixelVectorType = VectorPixelType;

    /** Prepare 400 lineal-energy bins (iunit=2) and nine-coefficient ion fits.
     * Diameter and radii are in um; betaRef is in Gy^-2. Coefficients are
     * loaded separately. Copies share fits but own numerical scratch buffers.
     */
    MicrodosimetricCalculator(size_t nybin_val, double celDiam, double domainRadius,
                             double nucleusRadius, double betaRef, int iunit_val, int mparased_val);

    /** Copy lineal-energy bin midpoints in keV/um into labels. */
    void get_Histo_X_Labels(std::vector<double>& labels) const;

    /** Evaluate the retained legacy kernel for comparison with the fast path.
     * Uses the same units and dose-weighted outputs as the fast kernel;
     * callers must supply valid inputs, loaded fits and initialized moments.
     */
    void calculateDoseWeightedMicrodosimetricFunction(
        VectorPixelType& microDosSpectra,
        double izz, double iAA, double ene, double dEdx, double dose,
        double& LinealEnergy_Dose, double& LinealEnergy_Dose_saturation_correctedS);

    /** Evaluate a dose-weighted spectrum and enabled lineal-energy moments.
     * izz is Z (1..18), iAA is atomic mass, energyPerNucleon is MeV/u,
     * dEdx is keV/um and dose is Gy. microDosSpectra receives dose*q(y),
     * where q integrates to one over ln(y). Moment references receive
     * dose*yD and dose*yS in Gy*keV/um, or zero when disabled. Inputs and
     * positive finite normalization are checked; scratch is not thread-safe.
     */
    void calculateDoseWeightedMicrodosimetricFunctionFast(
        VectorPixelType& microDosSpectra,
        double izz,
        double iAA,
        double energyPerNucleon,
        double dEdx,
        double dose,
        double& LinealEnergy_Dose,
        double& LinealEnergy_Dose_saturation_correctedS);

    /** Set the input path and immediately load the validated coefficient table. */
    void setTSEDfilename(const std::string& filename);
    /** Parse exactly 576 rows of nine finite coefficients into a shared const model.
     * Reject missing files, invalid active components and malformed row counts.
     */
    void loadIonData();
    /** Select moment calculations; the fast kernel always fills the spectrum.
     * linealEnergySpectra retains the legacy flag, while actor output flags
     * determine whether the computed spectrum is stored in voxel buffers.
     */
    void setCalculationFlags(bool linealEnergySpectra, bool doseAveragedLinealEnergySaturationCorrected, bool doseAveragedLinealEnergy) {
        fMicrodosimetricSpectra = linealEnergySpectra;
        fdoseAveragedLinealEnergySaturationCorrected = doseAveragedLinealEnergySaturationCorrected;
        fdoseAveragedLinealEnergy = doseAveragedLinealEnergy;
    }


};




#endif // GateAMFActor_h
