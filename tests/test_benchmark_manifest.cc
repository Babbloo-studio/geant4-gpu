#include <cassert>
#include <string>
#include <vector>

#include "BenchmarkDriver.hh"

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

    return 0;
}
