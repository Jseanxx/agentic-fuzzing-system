// Deep decode / lifecycle v2 harness.
//
// Goal: go beyond parser-only coverage and repeatedly exercise decode, line-based
// decode, streaming callbacks, predecoded IDWT, and single-tile reuse lifecycle
// on closely related codestream variants. This is aimed at higher-value bugs in
// tile/block/lifecycle paths rather than only main-header parsing.

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <functional>
#include <string>
#include <vector>

#include "decoder.hpp"

namespace {

enum class DeepDecodeStatus {
  kDeepDecoded,
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

struct StreamStats {
  uint64_t callbacks = 0;
  uint64_t checksum = 0;
};

std::vector<uint8_t> MakeVariant(const uint8_t *data, size_t size, size_t variant_index) {
  std::vector<uint8_t> variant(data, data + size);
  if (variant.empty()) {
    return variant;
  }

  switch (variant_index) {
    case 0:
      break;
    case 1: {
      const size_t trim = std::min<size_t>(variant.size() > 4 ? variant.size() / 8 : 1, 96);
      variant.resize(std::max<size_t>(1, variant.size() - trim));
      break;
    }
    case 2: {
      const size_t start = variant.size() / 2;
      const size_t stride = std::max<size_t>(1, (variant.size() / 17));
      for (size_t i = start; i < variant.size(); i += stride) {
        variant[i] = static_cast<uint8_t>(variant[i] ^ static_cast<uint8_t>(0x5A + (i & 0x0F)));
      }
      break;
    }
    default:
      break;
  }
  return variant;
}

void CaptureMetadata(open_htj2k::openhtj2k_decoder &decoder) {
  const uint16_t num_components = decoder.get_num_component();
  const uint16_t bounded_components = std::min<uint16_t>(num_components, 8);
  for (uint16_t c = 0; c < bounded_components; ++c) {
    (void)decoder.get_component_width(c);
    (void)decoder.get_component_height(c);
    (void)decoder.get_component_depth(c);
    (void)decoder.get_component_signedness(c);
  }
  (void)decoder.get_minumum_DWT_levels();
  (void)decoder.get_max_safe_reduce_NL();
  (void)decoder.get_colorspace();
}

void ConsumeRows(uint32_t y, int32_t *const *row_ptrs, uint16_t nc, StreamStats &stats) {
  stats.callbacks += 1;
  stats.checksum += y;
  const uint16_t bounded_components = std::min<uint16_t>(nc, 4);
  for (uint16_t c = 0; c < bounded_components; ++c) {
    if (row_ptrs[c] != nullptr) {
      stats.checksum += static_cast<uint64_t>(static_cast<uint32_t>(row_ptrs[c][0]));
    }
  }
}

void InvokeFull(open_htj2k::openhtj2k_decoder &decoder) {
  DecodeArtifacts artifacts;
  decoder.invoke(artifacts.planes, artifacts.widths, artifacts.heights, artifacts.depths, artifacts.signeds);
}

void InvokeLineBased(open_htj2k::openhtj2k_decoder &decoder) {
  DecodeArtifacts artifacts;
  decoder.invoke_line_based(artifacts.planes, artifacts.widths, artifacts.heights, artifacts.depths,
                            artifacts.signeds);
}

void InvokePredecoded(open_htj2k::openhtj2k_decoder &decoder) {
  DecodeArtifacts artifacts;
  decoder.invoke_line_based_predecoded(artifacts.planes, artifacts.widths, artifacts.heights,
                                       artifacts.depths, artifacts.signeds);
}

void InvokeStream(open_htj2k::openhtj2k_decoder &decoder, bool reuse_stream) {
  StreamStats stats;
  std::vector<uint32_t> widths;
  std::vector<uint32_t> heights;
  std::vector<uint8_t> depths;
  std::vector<bool> signeds;
  auto callback = [&stats](uint32_t y, int32_t *const *rows, uint16_t nc) { ConsumeRows(y, rows, nc, stats); };
  if (reuse_stream) {
    decoder.invoke_line_based_stream_reuse(callback, widths, heights, depths, signeds);
  } else {
    decoder.invoke_line_based_stream(callback, widths, heights, depths, signeds);
  }
  (void)stats;
}

enum class StageKind {
  kFullDecode,
  kLineBased,
  kStream,
  kPredecoded,
  kReuseStream,
};

const char *StageName(StageKind stage) {
  switch (stage) {
    case StageKind::kFullDecode:
      return "full-decode";
    case StageKind::kLineBased:
      return "line-based";
    case StageKind::kStream:
      return "stream";
    case StageKind::kPredecoded:
      return "predecoded";
    case StageKind::kReuseStream:
      return "reuse-stream";
  }
  return "unknown";
}

void RunStage(open_htj2k::openhtj2k_decoder &decoder, StageKind stage) {
  switch (stage) {
    case StageKind::kFullDecode:
      InvokeFull(decoder);
      break;
    case StageKind::kLineBased:
      InvokeLineBased(decoder);
      break;
    case StageKind::kStream:
      InvokeStream(decoder, /*reuse_stream=*/false);
      break;
    case StageKind::kPredecoded:
      InvokePredecoded(decoder);
      break;
    case StageKind::kReuseStream:
      InvokeStream(decoder, /*reuse_stream=*/true);
      break;
  }
}

DeepDecodeStatus DeepDecodeLifecycleOneInput(const uint8_t *data, size_t size, bool verbose) {
  if (data == nullptr || size < 4) {
    return DeepDecodeStatus::kRejected;
  }

  bool parse_started = false;
  bool deep_stage_started = false;
  bool any_deep_stage_completed = false;

  open_htj2k::openhtj2k_decoder decoder;
  decoder.enable_single_tile_reuse(true);

  try {
    const uint8_t stage_selector = (size > 1) ? data[1] : data[0];
    const StageKind primary_stage = (stage_selector % 3U) == 0U
                                       ? StageKind::kFullDecode
                                       : ((stage_selector % 3U) == 1U ? StageKind::kLineBased
                                                                      : StageKind::kStream);
    const bool try_predecoded_probe = (size <= 160) && ((data[size - 1] & 1U) != 0U);
    const bool try_reuse_probe = (size <= 160) && ((data[0] & 2U) != 0U);

    for (size_t variant_index = 0; variant_index < 2; ++variant_index) {
      std::vector<uint8_t> variant = MakeVariant(data, size, variant_index);
      if (variant.empty()) {
        continue;
      }

      decoder.init(variant.data(), variant.size(), /*reduce_NL=*/0, /*num_threads=*/1);
      decoder.parse();
      parse_started = true;
      CaptureMetadata(decoder);

      deep_stage_started = true;
      try {
        if (variant_index == 0) {
          if (verbose) {
            std::fprintf(stderr, "deep stage[%zu]=%s\n", variant_index, StageName(primary_stage));
          }
          RunStage(decoder, primary_stage);
          any_deep_stage_completed = true;
          if (try_predecoded_probe) {
            if (verbose) {
              std::fprintf(stderr, "deep stage[%zu]=%s\n", variant_index, StageName(StageKind::kPredecoded));
            }
            decoder.init(variant.data(), variant.size(), /*reduce_NL=*/0, /*num_threads=*/1);
            decoder.parse();
            CaptureMetadata(decoder);
            RunStage(decoder, StageKind::kPredecoded);
            any_deep_stage_completed = true;
          }
          if (try_reuse_probe) {
            if (verbose) {
              std::fprintf(stderr, "deep stage[%zu]=%s\n", variant_index, StageName(StageKind::kReuseStream));
            }
            decoder.init(variant.data(), variant.size(), /*reduce_NL=*/0, /*num_threads=*/1);
            decoder.parse();
            CaptureMetadata(decoder);
            RunStage(decoder, StageKind::kReuseStream);
            any_deep_stage_completed = true;
          }
        } else {
          if (verbose) {
            std::fprintf(stderr, "deep lifecycle probe[%zu]=reinit-parse-only\n", variant_index);
          }
        }
      } catch (const std::exception &stage_exc) {
        if (verbose) {
          std::fprintf(stderr, "deep stage exception[%zu]: %s\n", variant_index, stage_exc.what());
        }
      } catch (...) {
        if (verbose) {
          std::fprintf(stderr, "deep stage exception[%zu]: unknown\n", variant_index);
        }
      }
    }
  } catch (const std::exception &exc) {
    decoder.destroy();
    if (verbose) {
      std::fprintf(stderr, "deep decode lifecycle exception: %s\n", exc.what());
    }
    return (parse_started || deep_stage_started) ? DeepDecodeStatus::kPartialFailure
                                                 : DeepDecodeStatus::kRejected;
  } catch (...) {
    decoder.destroy();
    if (verbose) {
      std::fprintf(stderr, "deep decode lifecycle exception: unknown\n");
    }
    return (parse_started || deep_stage_started) ? DeepDecodeStatus::kPartialFailure
                                                 : DeepDecodeStatus::kRejected;
  }

  decoder.destroy();

  if (verbose) {
    std::fprintf(stderr, "deep decode lifecycle accepted input\n");
  }
  return any_deep_stage_completed ? DeepDecodeStatus::kDeepDecoded : DeepDecodeStatus::kRejected;
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  (void)DeepDecodeLifecycleOneInput(data, size, /*verbose=*/false);
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

  const DeepDecodeStatus status = DeepDecodeLifecycleOneInput(input.data(), input.size(), /*verbose=*/true);
  if (expect_ok && status != DeepDecodeStatus::kDeepDecoded) {
    return 1;
  }
  return 0;
}
#endif
