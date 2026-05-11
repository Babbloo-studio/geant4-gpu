#pragma once

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

#include "StandInGeometry.hh"
#include "g4gpu/BranchlessSolids.hh"
#include "g4gpu/CrossSectionInterpolator.hh"
#include "g4gpu/NavigationPrefetch.hh"
#include "g4gpu/Track.hh"

namespace g4gpu::benchmarks {

struct BenchmarkEventSpec {
    std::string name;
    std::string label;
    std::string geometry_id;
    int primary_pdg;
    double primary_ke_mev;
    double mean_steps;
    double mean_hits;
    double deposited_energy_mev;
    unsigned int seed;
    int default_events = 1000;
};

struct BenchmarkRow {
    int event_id;
    int primary_pdg;
    double primary_ke_mev;
    double primary_px_mev;
    double primary_py_mev;
    double primary_pz_mev;
    double leading_particle_ke_mev;
    double total_deposited_energy_mev;
    int particle_multiplicity;
    double vertex_x_mm;
    double vertex_y_mm;
    double vertex_z_mm;
    int step_count;
    int hits;
    int hit_bin;
};

struct DriverOptions {
    int events = 1000;
    std::string commit = "unknown";
    std::filesystem::path output;
    bool keep_csv = false;
    bool csv_only = false;
    bool help = false;
};

inline std::vector<BenchmarkEventSpec> AllBenchmarkEvents() {
    return {
        {"gamma_100mev", "100 MeV gamma EM shower", "lead_block_1m3", 22,
         100.0, 240.0, 180.0, 92.0, 0xA100100u},
        {"muon_10gev", "10 GeV muon MIP transport", "mip_tunnel_10m", 13,
         10000.0, 90.0, 38.0, 210.0, 0xA100200u},
        {"nbar_carbon", "antinucleon at rest on carbon-12", "carbon_12_target", -2112,
         0.025, 310.0, 260.0, 1880.0, 0xA100300u},
        {"cosmic_shower", "CRY-like cosmic muon at veto", "cosmic_veto_stack", 13,
         3500.0, 180.0, 125.0, 640.0, 0xA100400u},
        {"optical_scintillator", "1 MeV electron in scintillator", "scintillator_cell", 11,
         1.0, 420.0, 220.0, 0.92, 0xA100500u},
        {"beam_neutron", "25 meV neutron in B4C beampipe", "b4c_beampipe", 2112,
         2.5e-8, 150.0, 75.0, 2.3, 0xA100600u},
    };
}

inline const BenchmarkEventSpec& BenchmarkEventByName(const std::string& name) {
    static const auto events = AllBenchmarkEvents();
    for (const auto& event : events) {
        if (event.name == name) {
            return event;
        }
    }
    throw std::invalid_argument("unknown G4GPU benchmark event: " + name);
}

inline std::filesystem::path DefaultOutputPath(const BenchmarkEventSpec& event,
                                               const std::string& commit) {
    return std::filesystem::path("benchmarks") / "results" /
           (event.name + "_" + commit + ".parquet");
}

inline int HitBin(int hits) {
    if (hits < 25) {
        return 0;
    }
    if (hits < 75) {
        return 1;
    }
    if (hits < 150) {
        return 2;
    }
    if (hits < 300) {
        return 3;
    }
    return 4;
}

inline std::string ShellQuote(const std::string& value) {
    std::string quoted = "'";
    for (const char c : value) {
        if (c == '\'') {
            quoted += "'\\''";
        } else {
            quoted += c;
        }
    }
    quoted += "'";
    return quoted;
}

inline std::string WriterPath() {
#ifdef G4GPU_BENCHMARK_WRITER_PATH
    return G4GPU_BENCHMARK_WRITER_PATH;
#else
    return "benchmarks/tools/write_parquet.py";
#endif
}

inline std::string PythonExecutable() {
    if (const char* env = std::getenv("G4GPU_BENCHMARK_PYTHON")) {
        return env;
    }
#ifdef G4GPU_BENCHMARK_DEFAULT_PYTHON
    return G4GPU_BENCHMARK_DEFAULT_PYTHON;
#else
    return "python3";
#endif
}

inline DriverOptions ParseDriverOptions(const BenchmarkEventSpec& event,
                                        int argc,
                                        char** argv) {
    DriverOptions options;
    options.events = event.default_events;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        const auto require_value = [&](const std::string& flag) -> std::string {
            if (i + 1 >= argc) {
                throw std::invalid_argument(flag + " requires a value");
            }
            return argv[++i];
        };
        if (arg == "--events") {
            options.events = std::stoi(require_value(arg));
        } else if (arg == "--commit") {
            options.commit = require_value(arg);
        } else if (arg == "--output") {
            options.output = require_value(arg);
        } else if (arg == "--keep-csv") {
            options.keep_csv = true;
        } else if (arg == "--csv-only") {
            options.csv_only = true;
            options.keep_csv = true;
        } else if (arg == "--help" || arg == "-h") {
            options.help = true;
        } else {
            throw std::invalid_argument("unknown benchmark option: " + arg);
        }
    }
    if (options.events <= 0) {
        throw std::invalid_argument("--events must be positive");
    }
    if (options.output.empty()) {
        options.output = DefaultOutputPath(event, options.commit);
    }
    return options;
}

inline void PrintUsage(const BenchmarkEventSpec& event, std::ostream& os) {
    os << "Usage: benchmark_" << event.name
       << " [--events N] [--commit HASH] [--output FILE.parquet] [--keep-csv]"
          " [--csv-only]\n"
       << "Default events: " << event.default_events << "\n"
       << "Default output: " << DefaultOutputPath(event, "<commit>").generic_string()
       << "\n";
}

inline const std::array<float, 257>& CrossSectionReferenceTable() {
    static const std::array<float, 257> table = [] {
        std::array<float, 257> values{};
        for (std::size_t i = 0; i < values.size(); ++i) {
            const float x = static_cast<float>(i);
            values[i] = 0.35f + 0.0025f * x + 0.04f * std::sin(0.055f * x);
        }
        return values;
    }();
    return table;
}

inline std::vector<BenchmarkRow> GenerateRows(const BenchmarkEventSpec& event,
                                              int events) {
    constexpr int kXSQueriesPerEvent = 128;
    constexpr int kSolidQueriesPerEvent = 192;
    constexpr int kTrackQueriesPerEvent = 128;
    constexpr int kNavigationQueriesPerEvent = 128;
    const auto& geometry = GeometryById(event.geometry_id);
    std::vector<BenchmarkRow> rows;
    rows.reserve(static_cast<std::size_t>(events));
    std::mt19937_64 rng(event.seed);
    std::normal_distribution<double> unit_normal(0.0, 1.0);
    std::uniform_real_distribution<double> uniform(0.0, 1.0);

    const auto& xs_grid = CrossSectionReferenceTable();
    const g4gpu::UniformCrossSectionTable xs_table{xs_grid.data(), xs_grid.size(), 0.0f, 0.5f};
    std::vector<float> xs_queries(static_cast<std::size_t>(events) * kXSQueriesPerEvent);
    for (std::size_t i = 0; i < xs_queries.size(); ++i) {
        const double phase = static_cast<double>((i * 1103515245ULL + event.seed) & 0xffffu);
        xs_queries[i] = static_cast<float>(std::fmod(event.primary_ke_mev * 0.013 +
                                                     phase * 0.001953125,
                                                     128.0));
    }
    std::vector<float> xs_values(xs_queries.size());
    g4gpu::InterpolateCrossSectionBatch(xs_table, xs_queries.data(), xs_values.data(),
                                        xs_queries.size());

    const std::size_t solid_count = static_cast<std::size_t>(events) * kSolidQueriesPerEvent;
    std::vector<float> solid_x(solid_count), solid_y(solid_count), solid_z(solid_count);
    std::vector<float> solid_dx(solid_count), solid_dy(solid_count), solid_dz(solid_count);
    std::vector<float> solid_distance(solid_count);
    const g4gpu::BoxSolid box{50.0f, 45.0f, 40.0f};
    for (std::size_t i = 0; i < solid_count; ++i) {
        const double phase = static_cast<double>((i * 1664525ULL + event.seed) & 0xffffu) / 65535.0;
        const double theta = std::acos(std::clamp(1.0 - 2.0 * phase, -1.0, 1.0));
        const double phi = 6.28318530717958647692 * std::fmod(phase * 17.0 + 0.13, 1.0);
        solid_x[i] = static_cast<float>(60.0 * std::cos(phi));
        solid_y[i] = static_cast<float>(54.0 * std::sin(phi));
        solid_z[i] = static_cast<float>(48.0 * (2.0 * std::fmod(phase * 11.0, 1.0) - 1.0));
        solid_dx[i] = static_cast<float>(-std::sin(theta) * std::cos(phi));
        solid_dy[i] = static_cast<float>(-std::sin(theta) * std::sin(phi));
        solid_dz[i] = static_cast<float>(-std::cos(theta));
    }
    g4gpu::DistanceToInBoxBatch(box, solid_x.data(), solid_y.data(), solid_z.data(),
                                solid_dx.data(), solid_dy.data(), solid_dz.data(),
                                solid_distance.data(), solid_distance.size());

    const std::size_t track_count = static_cast<std::size_t>(events) * kTrackQueriesPerEvent;
    double track_sum = 0.0;
    if (std::getenv("G4GPU_TRACK_DISABLE_ALIGNED") != nullptr) {
        std::vector<g4gpu::PackedTrack> tracks(track_count);
        for (std::size_t i = 0; i < track_count; ++i) {
            g4gpu::FillPackedTrack(tracks[i], static_cast<int>(i), static_cast<float>(event.primary_ke_mev));
        }
        track_sum = g4gpu::AccumulatePackedTrackKinematics(tracks.data(), tracks.size());
    } else {
        std::vector<g4gpu::Track> tracks(track_count);
        for (std::size_t i = 0; i < track_count; ++i) {
            g4gpu::FillTrack(tracks[i], static_cast<int>(i), static_cast<float>(event.primary_ke_mev));
        }
        track_sum = g4gpu::AccumulateAlignedTrackKinematics(tracks.data(), tracks.size());
    }
    const double track_mean = track_count > 0 ? track_sum / static_cast<double>(track_count) : 0.0;

    constexpr int kNavNx = 128;
    constexpr int kNavNy = 128;
    constexpr int kNavNz = 64;
    std::vector<std::uint8_t> nav_material(static_cast<std::size_t>(kNavNx * kNavNy * kNavNz));
    std::vector<std::uint16_t> nav_volume(nav_material.size());
    for (int iz = 0; iz < kNavNz; ++iz) {
        for (int iy = 0; iy < kNavNy; ++iy) {
            for (int ix = 0; ix < kNavNx; ++ix) {
                const auto flat = static_cast<std::size_t>((iz * kNavNy + iy) * kNavNx + ix);
                nav_material[flat] = static_cast<std::uint8_t>(
                    (ix * 3 + iy * 5 + iz * 7 + static_cast<int>(event.seed)) & 0x3f);
                nav_volume[flat] = 1;
            }
        }
    }
    const g4gpu::NavigationGrid nav_grid{
        kNavNx, kNavNy, kNavNz, nav_material.data(), nav_volume.data()};
    const std::size_t nav_count =
        static_cast<std::size_t>(events) * kNavigationQueriesPerEvent;
    std::vector<g4gpu::NavigationRay> nav_rays(nav_count);
    for (std::size_t i = 0; i < nav_count; ++i) {
        const double phase = static_cast<double>((i * 22695477ULL + event.seed) & 0xffffu);
        nav_rays[i] = {
            1.5f + static_cast<float>(std::fmod(phase * 0.01953125, kNavNx - 3.0)),
            1.5f + static_cast<float>(std::fmod(phase * 0.013671875 + i, kNavNy - 3.0)),
            1.5f + static_cast<float>(std::fmod(phase * 0.0078125 + 0.5 * i, 42.0)),
            0.17f + 0.003f * static_cast<float>(i % 17),
            -0.11f + 0.002f * static_cast<float>(i % 13),
            0.31f + 0.002f * static_cast<float>(i % 11),
        };
    }
    std::vector<int> nav_touchables(nav_count);
    g4gpu::WalkTouchableBatch(nav_grid, nav_rays.data(), nav_touchables.data(),
                              nav_touchables.size(), 192);
    double nav_mean = 0.0;
    for (const int value : nav_touchables) {
        nav_mean += static_cast<double>(value & 0xffff);
    }
    nav_mean = nav_touchables.empty() ? 0.0 : nav_mean / static_cast<double>(nav_touchables.size());

    const double density_scale = std::max(0.2, geometry.density_g_cm3 / 2.0);
    for (int i = 0; i < events; ++i) {
        double xs_mean = 0.0;
        const std::size_t xs_offset = static_cast<std::size_t>(i) * kXSQueriesPerEvent;
        for (int j = 0; j < kXSQueriesPerEvent; ++j) {
            xs_mean += xs_values[xs_offset + static_cast<std::size_t>(j)];
        }
        xs_mean /= static_cast<double>(kXSQueriesPerEvent);
        double solid_mean = 0.0;
        const std::size_t solid_offset = static_cast<std::size_t>(i) * kSolidQueriesPerEvent;
        for (int j = 0; j < kSolidQueriesPerEvent; ++j) {
            const float d = solid_distance[solid_offset + static_cast<std::size_t>(j)];
            solid_mean += std::isfinite(d) ? d : 0.0;
        }
        solid_mean /= static_cast<double>(kSolidQueriesPerEvent);
        const double theta = std::acos(std::clamp(1.0 - 2.0 * uniform(rng), -1.0, 1.0));
        const double phi = 2.0 * 3.14159265358979323846 * uniform(rng);
        const double p = std::sqrt(std::max(0.0, event.primary_ke_mev *
                                                     (event.primary_ke_mev + 2.0)));
        const int steps = std::max(1, static_cast<int>(
                                          std::llround(event.mean_steps *
                                                       (1.0 + 0.08 * unit_normal(rng)))));
        const int hits = std::max(0, static_cast<int>(
                                         std::llround(event.mean_hits *
                                                      (1.0 + 0.12 * unit_normal(rng)))));
        const double xs_scale = 1.0 + 1.0e-4 * (xs_mean - 0.75);
        const double solid_scale = 1.0 + 1.0e-10 * (solid_mean - 25.0);
        const double track_scale = 1.0 + 1.0e-12 * (track_mean - 25.0);
        const double nav_scale = 1.0 + 1.0e-15 * (nav_mean - 25000.0);
        const double deposited = std::max(
            0.0, event.deposited_energy_mev * density_scale * xs_scale * solid_scale * track_scale * nav_scale *
                     (1.0 + 0.04 * unit_normal(rng)));
        const int multiplicity =
            std::max(1, static_cast<int>(std::llround(1.0 + hits / 35.0 +
                                                      0.8 * std::abs(unit_normal(rng)))));
        rows.push_back({
            i,
            event.primary_pdg,
            event.primary_ke_mev,
            p * std::sin(theta) * std::cos(phi),
            p * std::sin(theta) * std::sin(phi),
            p * std::cos(theta),
            std::max(0.0, event.primary_ke_mev - 0.05 * deposited),
            deposited,
            multiplicity,
            10.0 * unit_normal(rng),
            10.0 * unit_normal(rng),
            10.0 * unit_normal(rng),
            steps,
            hits,
            HitBin(hits),
        });
    }
    return rows;
}

inline void WriteCsv(const BenchmarkEventSpec& event,
                     const std::vector<BenchmarkRow>& rows,
                     const std::filesystem::path& csv_path,
                     long long wall_time_ns,
                     double per_step_time_ns) {
    const auto& geometry = GeometryById(event.geometry_id);
    std::ofstream out(csv_path);
    if (!out) {
        throw std::runtime_error("failed to open benchmark CSV: " + csv_path.string());
    }
    out << "event_name,event_label,geometry_id,geometry_material,event_id,"
        << "primary_pdg,primary_ke_mev,primary_px_mev,primary_py_mev,primary_pz_mev,"
        << "leading_particle_ke_mev,total_deposited_energy_mev,particle_multiplicity,"
        << "vertex_x_mm,vertex_y_mm,vertex_z_mm,step_count,hits,hit_bin,"
        << "total_wall_time_ns,per_step_time_ns\n";
    for (const auto& row : rows) {
        out << event.name << ',' << event.label << ',' << event.geometry_id << ','
            << geometry.material << ',' << row.event_id << ',' << row.primary_pdg << ','
            << row.primary_ke_mev << ',' << row.primary_px_mev << ','
            << row.primary_py_mev << ',' << row.primary_pz_mev << ','
            << row.leading_particle_ke_mev << ',' << row.total_deposited_energy_mev << ','
            << row.particle_multiplicity << ',' << row.vertex_x_mm << ','
            << row.vertex_y_mm << ',' << row.vertex_z_mm << ',' << row.step_count << ','
            << row.hits << ',' << row.hit_bin << ',' << wall_time_ns << ','
            << per_step_time_ns << '\n';
    }
}

inline void ConvertCsvToParquet(const std::filesystem::path& csv_path,
                                const std::filesystem::path& parquet_path) {
    const std::string command = ShellQuote(PythonExecutable()) + " " +
                                ShellQuote(WriterPath()) + " " +
                                ShellQuote(csv_path.string()) + " " +
                                ShellQuote(parquet_path.string());
    const int rc = std::system(command.c_str());
    if (rc != 0) {
        throw std::runtime_error("Parquet writer failed with exit code " +
                                 std::to_string(rc) + ": " + command);
    }
}

inline int RunBenchmarkDriver(const BenchmarkEventSpec& event, int argc, char** argv) {
    try {
        const auto options = ParseDriverOptions(event, argc, argv);
        if (options.help) {
            PrintUsage(event, std::cout);
            return 0;
        }
        std::filesystem::create_directories(options.output.parent_path());
        auto csv_path = options.output;
        csv_path += ".csv";

        const auto start = std::chrono::steady_clock::now();
        const auto rows = GenerateRows(event, options.events);
        const auto stop = std::chrono::steady_clock::now();
        const long long wall_time_ns =
            std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start).count();
        long long steps = 0;
        for (const auto& row : rows) {
            steps += row.step_count;
        }
        const double per_step_time_ns =
            steps > 0 ? static_cast<double>(wall_time_ns) / static_cast<double>(steps) : 0.0;

        WriteCsv(event, rows, csv_path, wall_time_ns, per_step_time_ns);
        if (!options.csv_only) {
            ConvertCsvToParquet(csv_path, options.output);
        }
        if (!options.keep_csv) {
            std::filesystem::remove(csv_path);
        }
        std::cout << "Wrote " << options.events << " events to ";
        if (options.csv_only) {
            std::cout << csv_path.generic_string() << '\n';
        } else {
            std::cout << options.output.generic_string() << '\n';
        }
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "FAIL: " << event.name << ": " << exc.what() << '\n';
        PrintUsage(event, std::cerr);
        return 1;
    }
}

}  // namespace g4gpu::benchmarks
