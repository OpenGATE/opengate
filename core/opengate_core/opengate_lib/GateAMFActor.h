/* AMF port from 624a6f863be8b90a2669e07b760efe07a1351dcb.
   Copyright (C): OpenGATE Collaboration. LGPL; see LICENSE.md. */
#ifndef GateAMFActor_h
#define GateAMFActor_h

#include "GateVActor.h"
#include "GateHelpersImage.h"
#include "G4SystemOfUnits.hh"
#include "itkImage.h"
#include "itkVectorImage.h"
#include <memory>
#include <vector>
#include <cmath>
#include <pybind11/stl.h>

class MicrodosimetricCalculator;

class GateAMFActor : public GateVActor {
public:
  using Image3DType = itk::Image<double, 3>;
  using ImageVectorType = itk::VectorImage<double, 3>;
  using VectorPixelType = ImageVectorType::PixelType;
  explicit GateAMFActor(py::dict &user_info);
  ~GateAMFActor() override;
  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  void BeginOfRunActionMasterThread(int run_id) override;
  int EndOfRunActionMasterThread(int run_id) override;
  void BeginOfEventAction(const G4Event *) override { ++NbOfEvent; }
  void SteppingAction(G4Step *step) override;
  void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }
  std::string GetPhysicalVolumeName() const { return fPhysicalVolumeName; }
  void GetVoxelPosition(G4Step *, G4ThreeVector &, bool &, Image3DType::IndexType &) const;
  double getDose(G4Step *) const;
  double GetStoppingPower(G4Step *) const;
  std::vector<double> GetHistogramLabels() const;
  void divideImage3DByImage3D(Image3DType::Pointer, Image3DType::Pointer);
  void divideVectorImageByScalarImage(ImageVectorType::Pointer, Image3DType::Pointer);
  void squareImage(Image3DType::Pointer);
  bool GetMicrodosimetricSpectraFlag() const { return fMicrodosimetricSpectra; }
  void SetMicrodosimetricSpectraFlag(bool b) { fMicrodosimetricSpectra = b; }
  bool GetDoseAveragedLinealEnergyFlag() const { return fdoseAveragedLinealEnergy; }
  void SetDoseAveragedLinealEnergyFlag(bool b) { fdoseAveragedLinealEnergy = b; }
  bool GetDoseAveragedLinealEnergySaturationCorrectedFlag() const { return fdoseAveragedLinealEnergySaturationCorrected; }
  void SetDoseAveragedLinealEnergySaturationCorrectedFlag(bool b) { fdoseAveragedLinealEnergySaturationCorrected = b; }
  void SetAlphaMCFMKMFlag(bool b) { fAlphaMCFMKMFlag = b; }
  void SetBetaMCFMKMFlag(bool b) { fBetaMCFMKMFlag = b; }
  void SetDomainRadius(double x) { fdomainRadiusInUm = x / CLHEP::um; }
  void SetNucleusRadius(double x) { fNucleusRadiusInUm = x / CLHEP::um; }
  void SetBetaRef(double x) { fBetaRefinGyminus2 = x * CLHEP::gray * CLHEP::gray; }
  void SetAlphaRef(double x) { fAlphaRefinGyminus1 = x * CLHEP::gray; }
  void SetAlphaNot(double x) { fAlphaNotinGyminus1 = x * CLHEP::gray; }

  Image3DType::Pointer cpp_amf_dose_image;
  ImageVectorType::Pointer cpp_amf_microdosimetric_spectra;
  Image3DType::Pointer cpp_amf_dose_averaged_lineal_energy_saturation_corrected;
  Image3DType::Pointer cpp_amf_dose_averaged_lineal_energy;
  Image3DType::Pointer cpp_amf_alpha_mcfmkm_image;
  Image3DType::Pointer cpp_amf_beta_mcfmkm_image;
  int NbOfEvent = 0;
  std::string fPhysicalVolumeName;
private:
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
  std::unique_ptr<MicrodosimetricCalculator> calculator;
};

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
    std::vector<std::vector<double>> IonData;
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


    // Private initialization function
    void initialize();

    inline int buildIonParamCombos(
          double depev, int ic1, int ie1, int ip1, double ratioc, double ratioe, double ratiop,
          IonParamCombo combos[8],          // output
          double& weightedA8                // output: Σ weight * A8
      ) const;

    inline double sedmeanFast(double x, bool depevZero, const IonParamCombo* combos, int nCombos) const;

    void getAparaion(const double& CelDiam, const double& energyPerNucleon, const int& iAA, const int& izz,
                     double& ratioc, double& ratioe, double& ratiop, int& ic1, int& ie1, int& ip1);

    inline double sedmean(double x, double depev, int ic1, int ie1, int ip1,
                   double ratioc, double ratioe, double ratiop, double Apara[]);
    inline double sedfunc(double x, double depev, const double Apara[], size_t size);

    public:

    // Pixel type alias exposed (if callers need it)
    using PixelVectorType = VectorPixelType;

    // Constructor
    MicrodosimetricCalculator(size_t nybin_val, double celDiam, double domainRadius,
                             double nucleusRadius, double betaRef, int iunit_val, int mparased_val);

    void get_Histo_X_Labels(std::vector<double>& labels) const;

    void calculateDoseWeightedMicrodosimetricFunction(
        VectorPixelType& microDosSpectra,
        double izz, double iAA, double ene, double dEdx, double dose,
        double& LinealEnergy_Dose, double& LinealEnergy_Dose_saturation_correctedS);

    void calculateDoseWeightedMicrodosimetricFunctionFast(
        VectorPixelType& microDosSpectra,
        double izz,
        double iAA,
        double energyPerNucleon,
        double dEdx,
        double dose,
        double& LinealEnergy_Dose,
        double& LinealEnergy_Dose_saturation_correctedS);

    void setTSEDfilename(const std::string& filename);
    void loadIonData();
    void setCalculationFlags(bool linealEnergySpectra, bool doseAveragedLinealEnergySaturationCorrected, bool doseAveragedLinealEnergy) {
        fMicrodosimetricSpectra = linealEnergySpectra;
        fdoseAveragedLinealEnergySaturationCorrected = doseAveragedLinealEnergySaturationCorrected;
        fdoseAveragedLinealEnergy = doseAveragedLinealEnergy;
    }


};




#endif // GateAMFActor_h
