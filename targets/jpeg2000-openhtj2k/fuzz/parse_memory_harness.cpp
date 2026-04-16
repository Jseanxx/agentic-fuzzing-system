// Parser-focused harness for codestream / marker parsing.
//
// Goal: isolate parser-side memory-safety findings with a shallower entrypoint
// than full decode+invoke, while still exercising real decoder object setup.

#include <cstdint>
#include <cstdio>
#include <exception>
#include <string>
#include <vector>

#include "decoder.hpp"

namespace {

enum class ParseStatus {
  kParsed,
  kRejected,
};

ParseStatus ParseOneInput(const uint8_t* data, size_t size, bool verbose) {
  if (data == nullptr || size == 0) {
    return ParseStatus::kRejected;
  }

  try {
    open_htj2k::openhtj2k_decoder decoder(data, size, /*reduce_NL=*/0, /*num_threads=*/1);
    decoder.parse();
  } catch (const std::exception& exc) {
    if (verbose) {
      std::fprintf(stderr, "parser rejected input: %s\n", exc.what());
    }
    return ParseStatus::kRejected;
  } catch (...) {
    if (verbose) {
      std::fprintf(stderr, "parser rejected input: unknown exception\n");
    }
    return ParseStatus::kRejected;
  }

  if (verbose) {
    std::fprintf(stderr, "parser accepted input\n");
  }
  return ParseStatus::kParsed;
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  (void)ParseOneInput(data, size, /*verbose=*/false);
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

  const ParseStatus status = ParseOneInput(input.data(), input.size(), /*verbose=*/true);
  if (expect_ok && status != ParseStatus::kParsed) {
    return 1;
  }
  return 0;
}
#endif
