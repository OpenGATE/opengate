/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigiCollectionNumpyWriter_h
#define GateDigiCollectionNumpyWriter_h

#include "GateVDigiAttribute.h"
#include <cstdint>
#include <fstream>
#include <mutex>
#include <string>
#include <vector>

/*
 * Writes a digi collection to a .npy file, one row per digi.
 * All threads append to the same file. The row count in the header is
 * updated at every flush, so the file stays readable if a run stops early.
 */
class GateDigiCollectionNumpyWriter {
public:
  // fixed length of string columns, longer strings are an error
  static constexpr size_t kStringLength = 64;

  GateDigiCollectionNumpyWriter(
      const std::string &filename,
      const std::vector<GateVDigiAttribute *> &attributes);

  ~GateDigiCollectionNumpyWriter();

  // append the first n digis of the calling thread
  void AppendRows(size_t n);

  void Flush();

  void Close();

protected:
  struct Field {
    GateVDigiAttribute *attribute;
    char type;
    size_t offset;
  };

  void WriteHeader();
  void FlushLocked();
  void WriteRowCount();
  void CopyString(char *dest, const std::string &s,
                  const GateVDigiAttribute *att) const;

  std::string fFilename;
  std::vector<Field> fFields;
  std::vector<std::pair<std::string, std::string>> fDescr;
  size_t fRowSize = 0;
  std::ofstream fFile;
  std::streampos fRowCountPosition;
  uint64_t fNumberOfRowsInFile = 0;
  uint64_t fNumberOfRowsInBuffer = 0;
  std::vector<char> fBuffer;
  std::mutex fMutex;
};

#endif // GateDigiCollectionNumpyWriter_h
