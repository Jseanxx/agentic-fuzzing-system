// Deep decode focus v3 harness.
//
// Goal: use v2 feedback to reduce shallow metadata/header-only crashes and bias
// execution toward deeper decode/tile/block/IDWT paths. v3 avoids the decoder
// metadata getter probes that dominated v2 and instead focuses on repeated
// parse->decode cycles with closely related codestream variants.

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <string>
#include <vector>

#include "decoder.hpp"

namespace {

enum class DeepDecodeFocusStatus {
  kDecoded,
  kRejected,
  kPartialFailure,
};

struct DecodeArtifacts {
  std::vector<int32_t *> planes;
  std::vector<uint32_t> widths;
  std::vector<uint32_t> heights;
  std::vector<uint8_t> depths;
  std::vector<bool> signeds;

  void reset() {
    for (int32_t *plane : planes) {
      delete[] plane;
    }
    planes.clear();
    widths.clear();
    heights.clear();
    depths.clear();
    signeds.clear();
  }

  ~DecodeArtifacts() { reset(); }
};

enum class StageKind {
  kLineBased,
  kFullDecode,
  kStream,
};

const char *StageName(StageKind stage) {
  switch (stage) {
    case StageKind::kLineBased:
      return "line-based";
    case StageKind::kFullDecode:
      return "full-decode";
    case StageKind::kStream:
      return "stream";
  }
  return "unknown";
}

void InvokeLineBased(open_htj2k::openhtj2k_decoder &decoder) {
  DecodeArtifacts artifacts;
  decoder.invoke_line_based(artifacts.planes, artifacts.widths, artifacts.heights, artifacts.depths,
                            artifacts.signeds);
}

void InvokeFull(open_htj2k::openhtj2k_decoder &decoder) {
  DecodeArtifacts artifacts;
  decoder.invoke(artifacts.planes, artifacts.widths, artifacts.heights, artifacts.depths, artifacts.signeds);
}

void InvokeStream(open_htj2k::openhtj2k_decoder &decoder) {
  std::vector<uint32_t> widths;
  std::vector<uint32_t> heights;
  std::vector<uint8_t> depths;
  std::vector<bool> signeds;
  uint64_t checksum = 0;
  auto callback = [&checksum](uint32_t y, int32_t *const *rows, uint16_t nc) {
    checksum += y;
    const uint16_t bounded = std::min<uint16_t>(nc, 4);
    for (uint16_t c = 0; c < bounded; ++c) {
      if (rows[c] != nullptr) {
        checksum += static_cast<uint64_t>(static_cast<uint32_t>(rows[c][0]));
      }
    }
  };
  decoder.invoke_line_based_stream(callback, widths, heights, depths, signeds);
  (void)checksum;
}

void RunStage(open_htj2k::openhtj2k_decoder &decoder, StageKind stage) {
  switch (stage) {
    case StageKind::kLineBased:
      InvokeLineBased(decoder);
      break;
    case StageKind::kFullDecode:
      InvokeFull(decoder);
      break;
    case StageKind::kStream:
      InvokeStream(decoder);
      break;
  }
}

std::vector<uint8_t> MakeVariant(const uint8_t *data, size_t size, size_t variant_index) {
  (void)variant_index;
  std::vector<uint8_t> variant(data, data + size);
  return variant;
}

DeepDecodeFocusStatus DeepDecodeFocusV3OneInput(const uint8_t *data, size_t size, bool verbose) {
  if (data == nullptr || size < 8) {
    return DeepDecodeFocusStatus::kRejected;
  }

  bool parse_started = false;
  bool deep_stage_started = false;
  bool any_stage_completed = false;

  const uint8_t stage_selector = static_cast<uint8_t>(size & 0x07U);
  const StageKind primary_stage = (stage_selector >= 4U) ? StageKind::kFullDecode : StageKind::kLineBased;
  const StageKind secondary_stage = (stage_selector & 0x02U) ? StageKind::kStream : StageKind::kLineBased;
  const uint8_t primary_reduce = 0U;
  const uint8_t secondary_reduce = (size > 96U) ? static_cast<uint8_t>((data[size / 2] & 0x01U)) : 0U;

  open_htj2k::openhtj2k_decoder decoder;
  decoder.enable_single_tile_reuse(true);

  try {
    for (size_t variant_index = 0; variant_index < 3; ++variant_index) {
      std::vector<uint8_t> variant = MakeVariant(data, size, variant_index);
      if (variant.empty()) {
        continue;
      }

      const bool run_deep_stage = (variant_index == 0);
      const uint8_t reduce_nl = (variant_index == 0) ? primary_reduce : secondary_reduce;

      decoder.init(variant.data(), variant.size(), reduce_nl, /*num_threads=*/1);
      decoder.parse();
      parse_started = true;

      if (!run_deep_stage) {
        continue;
      }

      deep_stage_started = true;
      try {
        const StageKind stage = (variant_index == 0) ? primary_stage : secondary_stage;
        if (verbose) {
          std::fprintf(stderr, "v3 stage[%zu]=%s reduce=%u size=%zu\n", variant_index, StageName(stage),
                       static_cast<unsigned>(reduce_nl), variant.size());
        }
        RunStage(decoder, stage);
        any_stage_completed = true;
      } catch (const std::exception &stage_exc) {
        if (verbose) {
          std::fprintf(stderr, "v3 stage exception[%zu]: %s\n", variant_index, stage_exc.what());
        }
      } catch (...) {
        if (verbose) {
          std::fprintf(stderr, "v3 stage exception[%zu]: unknown\n", variant_index);
        }
      }
    }
  } catch (const std::exception &exc) {
    decoder.destroy();
    if (verbose) {
      std::fprintf(stderr, "deep decode focus v3 exception: %s\n", exc.what());
    }
    return (parse_started || deep_stage_started) ? DeepDecodeFocusStatus::kPartialFailure
                                                 : DeepDecodeFocusStatus::kRejected;
  } catch (...) {
    decoder.destroy();
    if (verbose) {
      std::fprintf(stderr, "deep decode focus v3 exception: unknown\n");
    }
    return (parse_started || deep_stage_started) ? DeepDecodeFocusStatus::kPartialFailure
                                                 : DeepDecodeFocusStatus::kRejected;
  }

  decoder.destroy();
  if (verbose) {
    std::fprintf(stderr, "deep decode focus v3 accepted input\n");
  }
  return any_stage_completed ? DeepDecodeFocusStatus::kDecoded : DeepDecodeFocusStatus::kRejected;
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  (void)DeepDecodeFocusV3OneInput(data, size, /*verbose=*/false);
  return 0;
}

#ifndef OPENHTJ2K_LIBFUZZER
namespace {

bool ReadFile(const char *path, std::vector<uint8_t> &out) {
  FILE *fp = std::fopen(path, "rb");
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

int main(int argc, char **argv) {
  bool expect_ok = false;
  const char *input_path = nullptr;

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

  const DeepDecodeFocusStatus status = DeepDecodeFocusV3OneInput(input.data(), input.size(), /*verbose=*/true);
  if (expect_ok && status != DeepDecodeFocusStatus::kDecoded) {
    return 1;
  }
  return 0;
}
#endif
