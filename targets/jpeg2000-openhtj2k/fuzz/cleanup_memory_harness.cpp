// Cleanup-focused harness for partial decode / exceptional cleanup paths.
//
// Goal: stress allocation/free lifecycle and exceptional paths that may expose
// UAF, invalid free, double free, stale-pointer, or invalid write bugs.

#include <cstdint>
#include <cstdio>
#include <exception>
#include <string>
#include <vector>

#include "decoder.hpp"

namespace {

enum class CleanupStatus {
  kDecoded,
  kRejected,
  kPartialFailure,
};

void FreePlanes(std::vector<int32_t*>& planes) {
  for (int32_t* plane : planes) {
    delete[] plane;
  }
  planes.clear();
}

CleanupStatus CleanupStressOneInput(const uint8_t* data, size_t size, bool verbose) {
  if (data == nullptr || size == 0) {
    return CleanupStatus::kRejected;
  }

  std::vector<int32_t*> planes;
  std::vector<uint32_t> widths;
  std::vector<uint32_t> heights;
  std::vector<uint8_t> depths;
  std::vector<bool> signeds;
  bool parse_succeeded = false;
  bool invoke_started = false;

  try {
    open_htj2k::openhtj2k_decoder decoder(data, size, /*reduce_NL=*/0, /*num_threads=*/1);
    decoder.parse();
    parse_succeeded = true;
    invoke_started = true;
    decoder.invoke(planes, widths, heights, depths, signeds);
    FreePlanes(planes);
  } catch (const std::exception& exc) {
    FreePlanes(planes);
    if (verbose) {
      std::fprintf(stderr, "cleanup path exception: %s\n", exc.what());
    }
    return (parse_succeeded || invoke_started) ? CleanupStatus::kPartialFailure : CleanupStatus::kRejected;
  } catch (...) {
    FreePlanes(planes);
    if (verbose) {
      std::fprintf(stderr, "cleanup path exception: unknown\n");
    }
    return (parse_succeeded || invoke_started) ? CleanupStatus::kPartialFailure : CleanupStatus::kRejected;
  }

  if (verbose) {
    std::fprintf(stderr, "cleanup stress accepted input: %zu component(s)\n", depths.size());
  }
  return CleanupStatus::kDecoded;
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  (void)CleanupStressOneInput(data, size, /*verbose=*/false);
  return 0;
}

#ifndef OPENHTJ2K_LIBFUZZER
namespace {

bool ReadFile(const char* path, std::vector<uint8_t>& out) {
  FILE* fp = std::fopen(path, "rb");
  if (fp == nullptr) {
    std::fprintf(stderr, "failed to open input: %s\n", path);
    return false;
  }

  if (std::fseek(fp, 0, SEEK_END) != 0) {
    std::fclose(fp);
    return false;
  }
  const long file_size = std::ftell(fp);
  if (file_size < 0) {
    std::fclose(fp);
    return false;
  }
  if (std::fseek(fp, 0, SEEK_SET) != 0) {
    std::fclose(fp);
    return false;
  }

  out.resize(static_cast<size_t>(file_size));
  const size_t bytes_read = out.empty() ? 0 : std::fread(out.data(), 1, out.size(), fp);
  std::fclose(fp);

  if (bytes_read != out.size()) {
    std::fprintf(stderr, "short read: %s\n", path);
    out.clear();
    return false;
  }
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  bool expect_ok = false;
  const char* input_path = nullptr;

  for (int i = 1; i < argc; ++i) {
    const std::string arg(argv[i]);
    if (arg == "--expect-ok") {
      expect_ok = true;
    } else {
      input_path = argv[i];
    }
  }

  if (input_path == nullptr) {
    std::fprintf(stderr, "usage: %s [--expect-ok] <input.j2k|input.j2c|input.jph>\n", argv[0]);
    return 2;
  }

  std::vector<uint8_t> input;
  if (!ReadFile(input_path, input)) {
    return 2;
  }

  const CleanupStatus status = CleanupStressOneInput(input.data(), input.size(), /*verbose=*/true);
  if (expect_ok && status != CleanupStatus::kDecoded) {
    return 1;
  }
  return 0;
}
#endif
