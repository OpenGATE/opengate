/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVolumeVoxelizer.h"
#include "G4Navigator.hh"
#include "G4PhysicalVolumeStore.hh"
#include "indicators.hpp"
#include "itkImageRegionIteratorWithIndex.h"

GateVolumeVoxelizer::GateVolumeVoxelizer() { fImage = ImageType::New(); }

void GateVolumeVoxelizer::Voxelize() {
  // get navigator for world
  auto pvs = G4PhysicalVolumeStore::GetInstance();
  auto world = pvs->GetVolume("world");
  auto nav = new G4Navigator();
  nav->SetWorldVolume(world);

  // init to loop the image
  fImage->FillBuffer(0);
  auto index = ImageType::IndexType();
  auto point = ImageType::PointType();

  // init labels
  fLabels.clear();
  fLabels["world"] = 0;

  // progress bar
  using namespace indicators;
  int interval = 1000;
  auto n = fImage->GetLargestPossibleRegion().GetNumberOfPixels() / interval;
  ProgressBar bar{option::BarWidth{50},
                  option::Start{""},
                  option::Fill{"■"},
                  option::Lead{"■"},
                  option::End{""},
                  option::ShowElapsedTime{true},
                  option::ShowRemainingTime{true},
                  option::MaxProgress{n}};

  // main loop
  using IteratorType = itk::ImageRegionIteratorWithIndex<ImageType>;
  IteratorType outputIt(fImage, fImage->GetRequestedRegion());
  outputIt.GoToBegin();
  int i = 0;
  indicators::show_console_cursor(false);
  while (!outputIt.IsAtEnd()) {
    index = outputIt.GetIndex();
    fImage->TransformIndexToPhysicalPoint(index, point);
    G4ThreeVector p = {point[0], point[1], point[2]};
    auto phys = nav->LocateGlobalPointAndSetup(p);
    if (phys != nullptr) {
      auto name = phys->GetName();
      if (fLabels.count(name) == 0) {
        fLabels[name] = fLabels.size();
      }
      ImageType::PixelType l = fLabels[name];
      outputIt.Set(l);
    }
    ++outputIt;
    ++i;
    if (i == interval) {
      bar.tick(); // very slow if too often
      i = 0;
    }
  }
  indicators::show_console_cursor(true);
}
