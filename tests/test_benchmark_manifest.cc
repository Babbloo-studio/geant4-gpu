#include <cassert>
#include <string>
#include <vector>

#include "BenchmarkDriver.hh"
#include "CanonicalExamples.hh"

int main() {
    const auto events = g4gpu::benchmarks::AllBenchmarkEvents();
    const std::vector<std::string> expected_names = {
        "gamma_100mev",
        "muon_10gev",
        "nbar_carbon",
        "cosmic_shower",
        "optical_scintillator",
        "beam_neutron",
    };

    assert(events.size() == expected_names.size());
    for (std::size_t i = 0; i < expected_names.size(); ++i) {
        assert(events[i].name == expected_names[i]);
        assert(events[i].default_events == 1000);
        const auto output =
            g4gpu::benchmarks::DefaultOutputPath(events[i], "abc1234").generic_string();
        assert(output == "benchmarks/results/" + expected_names[i] + "_abc1234.parquet");
    }

    const auto canonical = g4gpu::benchmarks::AllCanonicalExamples();
    struct ExpectedCanonical {
        std::string name;
        std::string source_path;
        std::string executable;
        std::string macro;
    };
    const std::vector<ExpectedCanonical> expected_canonical = {
        {"basic_b1", "examples/basic/B1", "exampleB1", "run1.mac"},
        {"testem0", "examples/extended/electromagnetic/TestEm0", "TestEm0", "TestEm0.in"},
        {"hadr01", "examples/extended/hadronic/Hadr01", "Hadr01", "hadr01.in"},
        {"hadr02", "examples/extended/hadronic/Hadr02", "Hadr02", "hadr02.in"},
        {"opnovice2", "examples/extended/optical/OpNovice2", "OpNovice2", "electron.mac"},
        {"par01", "examples/extended/parameterisations/Par01", "examplePar01", "examplePar01.in"},
    };

    assert(canonical.size() == expected_canonical.size());
    for (std::size_t i = 0; i < expected_canonical.size(); ++i) {
        assert(canonical[i].name == expected_canonical[i].name);
        assert(canonical[i].source_path == expected_canonical[i].source_path);
        assert(canonical[i].executable == expected_canonical[i].executable);
        assert(canonical[i].macro == expected_canonical[i].macro);
        assert(!canonical[i].label.empty());
        const auto output = g4gpu::benchmarks::CanonicalLogPath(canonical[i], "abc1234")
                                .generic_string();
        assert(output == "benchmarks/results/canonical/" + expected_canonical[i].name +
                             "_abc1234.log");
        assert(g4gpu::benchmarks::CanonicalExampleByName(expected_canonical[i].name).name ==
               expected_canonical[i].name);
    }

    return 0;
}
