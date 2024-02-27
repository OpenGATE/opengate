/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDoseSpeedTestActor_h
#define GateDoseSpeedTestActor_h

#include "G4Cache.hh"
#include "G4NistManager.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateHelpers.h"
#include "GateVActor.h"
#include "itkImage.h"
#include "itkImageRegionIterator.h"
#include <atomic>
#include <deque>
#include <memory>
#include <pybind11/stl.h>
#include <stdlib.h>
#include <vector>

#define CACHELINESIZE 64

namespace py = pybind11;

struct dose_bin {
  alignas(CACHELINESIZE) std::atomic<double> dep;
  dose_bin() { dep = 0; }

  dose_bin &operator+=(const double a) {
    atomic_add_double(dep, a);
    return *this;
  }
};

// From https://github.com/zhourrr/aligned-memory-allocator
// A minimal implementation of an allocator for C++ Standard Library, which
// allocates aligned memory (specified by the alignment argument).
template <typename T, std::size_t alignment> class AlignedAllocator {
public:
  using value_type = T;

public:
  // According to Microsoft's documentation, default ctor is not required
  // by C++ Standard Library.
  AlignedAllocator() noexcept {};

  template <typename U>
  AlignedAllocator(const AlignedAllocator<U, alignment> &other) noexcept {};

  template <typename U>
  inline bool
  operator==(const AlignedAllocator<U, alignment> &other) const noexcept {
    return true;
  }

  template <typename U>
  inline bool
  operator!=(const AlignedAllocator<U, alignment> &other) const noexcept {
    return false;
  }

  template <typename U> struct rebind {
    using other = AlignedAllocator<U, alignment>;
  };

  // STL containers call this function to allocate unintialized memory block to
  // store (no more than n) elements of type T (value_type).
  inline value_type *allocate(const std::size_t n) const {
    auto size = n;
    /*
      If you wish, for some strange reason, that the size of allocated buffer is
      also aligned to alignment, uncomment the following statement.

      Note: this increases the size of underlying memory, but STL containers
      still treat it as a memory block of size n, i.e., STL containers will not
      put more than n elements into the returned memory.
    */
    // size = (n + alignment - 1) / alignment * alignment;
    value_type *ptr;
    auto ret = posix_memalign((void **)&ptr, alignment, sizeof(T) * size);
    if (ret != 0)
      throw std::bad_alloc();
    return ptr;
  };

  // STL containers call this function to free a memory block beginning at a
  // specified position.
  inline void deallocate(value_type *const ptr, std::size_t n) const noexcept {
    free(ptr);
  }
};

class GateDoseSpeedTestActor : public GateVActor {

public:
  // Constructor
  GateDoseSpeedTestActor(py::dict &user_info);

  ~GateDoseSpeedTestActor();

  // Main function called every step in attached volume
  virtual void SteppingAction(G4Step *) override;

  // Called every time a Run starts (all threads)
  virtual void BeginOfRunAction(const G4Run *run) override;

  virtual void EndOfRunAction(const G4Run *run) override;

  virtual void EndSimulationAction() override;

  // Called from the python-side when engines are initialized
  virtual void ActorInitialize() override;

  // pre-fill the vectors into which dose is written
  virtual void PrepareStorage();

  virtual void PrepareStorageLocal();

  // prepare the dose images
  void PrepareOutput();

  void WriteOutputToImageLocal();

  // Image type is 3D float by default
  // TODO double precision required
  using ImageType = itk::Image<double, 3>;
  using ImageIteratorType = itk::ImageRegionIterator<ImageType>;
  using RegionType = ImageType::RegionType;

  // The image is accessible on py side (shared by all threads)
  ImageType::Pointer cpp_reference_image;
  ImageType::Pointer cpp_image;

  using deposit_map_type = std::deque<dose_bin>;
  //  using deposit_map_type = std::deque<dose_bin, AlignedAllocator<dose_bin,
  //  CACHELINESIZE>>;
  deposit_map_type deposit_vector;

  std::vector<double> deposit_vector_standard;

  std::vector<std::atomic<double>> *deposit_vector_atomic_pointer{};

  std::string fPhysicalVolumeName;

  int GetTotalReattemptsAtomicAdd() { return (int)ftotalReattemptsAtomicAdd; }

  int GetTotalDepositWrites() { return (int)ftotalDepositWrites; }

protected:
  struct threadLocalT {
    std::vector<double> deposit_vector_local;
  };
  G4Cache<threadLocalT> fThreadLocalData;

private:
  G4ThreeVector fInitialTranslation;
  std::string fstorageMethod;
  int fnumberOfVoxels;
  double fVoxelVolume;
  ImageType::SizeType fimageSize;
  int fNumberOfThreads;
  std::atomic<int> ftotalReattemptsAtomicAdd = 0;
  std::atomic<int> ftotalDepositWrites = 0;
};

#endif // GateDoseSpeedTestActor_h
