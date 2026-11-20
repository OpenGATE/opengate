/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiCollectionNumpyWriter.h"
#include "../GateHelpers.h"
#include <cstring>
#include <iomanip>
#include <sstream>

static_assert(sizeof(int) == 4, "the numpy output expects a 32 bit int");

// the header says little endian ('<'), like all platforms GATE runs on
namespace {
constexpr size_t kFlushSize = 16 * 1024 * 1024;
constexpr size_t kRowCountWidth = 20;
} // namespace

GateDigiCollectionNumpyWriter::GateDigiCollectionNumpyWriter(
    const std::string &filename,
    const std::vector<GateVDigiAttribute *> &attributes)
    : fFilename(filename) {
  const std::string string_type = "|S" + std::to_string(kStringLength);
  for (auto *att : attributes) {
    const auto name = att->GetDigiAttributeName();
    const auto type = att->GetDigiAttributeType();
    Field field{att, type, fRowSize};
    if (type == 'D') {
      fDescr.emplace_back(name, "<f8");
      fRowSize += sizeof(double);
    } else if (type == 'I') {
      fDescr.emplace_back(name, "<i4");
      fRowSize += sizeof(int32_t);
    } else if (type == 'L') {
      fDescr.emplace_back(name, "<i8");
      fRowSize += sizeof(int64_t);
    } else if (type == '3') {
      fDescr.emplace_back(name + "_X", "<f8");
      fDescr.emplace_back(name + "_Y", "<f8");
      fDescr.emplace_back(name + "_Z", "<f8");
      fRowSize += 3 * sizeof(double);
    } else if (type == 'S' || type == 'U') {
      fDescr.emplace_back(name, string_type);
      fRowSize += kStringLength;
    } else {
      std::ostringstream oss;
      oss << "The digi attribute '" << name << "' has the type '" << type
          << "', which cannot be written to a numpy file.";
      Fatal(oss.str());
    }
    fFields.push_back(field);
  }
  if (fFields.empty()) {
    Fatal("Cannot write the numpy file '" + fFilename +
          "' because the digi collection has no attributes.");
  }

  fFile.open(fFilename, std::ios::binary | std::ios::trunc);
  if (!fFile.is_open()) {
    Fatal("Cannot create the numpy output file '" + fFilename +
          "'. Check that the output folder exists and is writable.");
  }
  WriteHeader();
}

GateDigiCollectionNumpyWriter::~GateDigiCollectionNumpyWriter() {
  try {
    Close();
  } catch (...) {
  }
}

void GateDigiCollectionNumpyWriter::WriteHeader() {
  std::ostringstream oss;
  oss << "{'descr': [";
  for (size_t i = 0; i < fDescr.size(); i++) {
    if (i > 0)
      oss << ", ";
    oss << "('" << fDescr[i].first << "', '" << fDescr[i].second << "')";
  }
  oss << "], 'fortran_order': False, 'shape': (";
  const auto before = oss.str();
  const std::string after = ",), }";

  // the header is padded with spaces so that the data starts at a multiple
  // of 64 bytes, and ends with a newline
  const auto text_size = before.size() + kRowCountWidth + after.size() + 1;
  size_t prefix_size = 10; // magic, version, uint16 header length
  auto total = (prefix_size + text_size + 63) / 64 * 64;
  char version = 1;
  if (total - prefix_size > 65535) {
    version = 2; // uint32 header length
    prefix_size = 12;
    total = (prefix_size + text_size + 63) / 64 * 64;
  }
  const auto header_size = total - prefix_size;
  const auto padding = header_size - text_size;

  const char magic[] = {'\x93', 'N', 'U', 'M', 'P', 'Y'};
  fFile.write(magic, sizeof(magic));
  const char v[] = {version, 0};
  fFile.write(v, 2);
  const auto n = prefix_size == 10 ? 2 : 4;
  for (int i = 0; i < n; i++) {
    const char b = static_cast<char>((header_size >> (8 * i)) & 0xff);
    fFile.write(&b, 1);
  }
  fFile.write(before.data(), static_cast<std::streamsize>(before.size()));
  fRowCountPosition = fFile.tellp();
  fFile.write(std::string(kRowCountWidth, ' ').data(), kRowCountWidth);
  const auto end = after + std::string(padding, ' ') + "\n";
  fFile.write(end.data(), static_cast<std::streamsize>(end.size()));
  WriteRowCount();
}

void GateDigiCollectionNumpyWriter::WriteRowCount() {
  std::ostringstream oss;
  oss << std::setw(kRowCountWidth) << fNumberOfRowsInFile;
  const auto end = fFile.tellp();
  fFile.seekp(fRowCountPosition);
  fFile.write(oss.str().data(), kRowCountWidth);
  fFile.seekp(end);
}

void GateDigiCollectionNumpyWriter::CopyString(
    char *dest, const std::string &s, const GateVDigiAttribute *att) const {
  if (s.size() > kStringLength) {
    std::ostringstream oss;
    oss << "The value '" << s << "' of the digi attribute '"
        << att->GetDigiAttributeName() << "' is longer than " << kStringLength
        << " characters, the limit of the numpy output ('" << fFilename
        << "'). Use a ROOT output instead.";
    Fatal(oss.str());
  }
  std::memcpy(dest, s.data(), s.size());
}

void GateDigiCollectionNumpyWriter::AppendRows(const size_t n) {
  if (n == 0)
    return;

  // fill the rows of this thread first, outside the lock
  std::vector<char> rows(n * fRowSize, 0);
  for (const auto &f : fFields) {
    if (static_cast<size_t>(f.attribute->GetSize()) < n) {
      Fatal("The digi attribute '" + f.attribute->GetDigiAttributeName() +
            "' has fewer values than the digi collection.");
    }
    char *p = rows.data() + f.offset;
    if (f.type == 'D') {
      const auto &v = f.attribute->GetDValues();
      for (size_t i = 0; i < n; i++)
        std::memcpy(p + i * fRowSize, &v[i], sizeof(double));
    } else if (f.type == 'I') {
      const auto &v = f.attribute->GetIValues();
      for (size_t i = 0; i < n; i++)
        std::memcpy(p + i * fRowSize, &v[i], sizeof(int32_t));
    } else if (f.type == 'L') {
      const auto &v = f.attribute->GetLValues();
      for (size_t i = 0; i < n; i++)
        std::memcpy(p + i * fRowSize, &v[i], sizeof(int64_t));
    } else if (f.type == '3') {
      const auto &v = f.attribute->Get3Values();
      for (size_t i = 0; i < n; i++) {
        const double xyz[3] = {v[i].x(), v[i].y(), v[i].z()};
        std::memcpy(p + i * fRowSize, xyz, sizeof(xyz));
      }
    } else if (f.type == 'S') {
      const auto &v = f.attribute->GetSValues();
      for (size_t i = 0; i < n; i++)
        CopyString(p + i * fRowSize, v[i], f.attribute);
    } else if (f.type == 'U') {
      const auto &v = f.attribute->GetUValues();
      for (size_t i = 0; i < n; i++)
        CopyString(p + i * fRowSize, v[i]->fID, f.attribute);
    }
  }

  std::lock_guard<std::mutex> lock(fMutex);
  if (!fFile.is_open()) {
    Fatal("Cannot add digis to the numpy file '" + fFilename +
          "' because it is already closed.");
  }
  fBuffer.insert(fBuffer.end(), rows.begin(), rows.end());
  fNumberOfRowsInBuffer += n;
  if (fBuffer.size() >= kFlushSize)
    FlushLocked();
}

void GateDigiCollectionNumpyWriter::FlushLocked() {
  if (!fFile.is_open() || fBuffer.empty())
    return;
  fFile.write(fBuffer.data(), static_cast<std::streamsize>(fBuffer.size()));
  fNumberOfRowsInFile += fNumberOfRowsInBuffer;
  fNumberOfRowsInBuffer = 0;
  fBuffer.clear();
  WriteRowCount();
  fFile.flush();
  if (!fFile) {
    Fatal("Error while writing the numpy file '" + fFilename + "'.");
  }
}

void GateDigiCollectionNumpyWriter::Flush() {
  std::lock_guard<std::mutex> lock(fMutex);
  FlushLocked();
}

void GateDigiCollectionNumpyWriter::Close() {
  std::lock_guard<std::mutex> lock(fMutex);
  if (!fFile.is_open())
    return;
  FlushLocked();
  fFile.close();
}
