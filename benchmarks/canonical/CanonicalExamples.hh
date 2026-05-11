#pragma once

#include <filesystem>
#include <stdexcept>
#include <string>
#include <vector>

namespace g4gpu::benchmarks {

struct CanonicalExampleSpec {
    std::string name;
    std::string label;
    std::string category;
    std::string source_path;
    std::string executable;
    std::string macro;
};

inline std::vector<CanonicalExampleSpec> AllCanonicalExamples() {
    return {
        {"basic_b1", "BasicExample B1 detector sanity baseline", "basic",
         "examples/basic/B1", "exampleB1", "run1.mac"},
        {"testem0", "TestEm0 electromagnetic material scan", "electromagnetic",
         "examples/extended/electromagnetic/TestEm0", "TestEm0", "TestEm0.in"},
        {"hadr01", "Hadr01 hadron stopping and interaction length", "hadronic",
         "examples/extended/hadronic/Hadr01", "Hadr01", "hadr01.in"},
        {"hadr02", "Hadr02 hadronic final-state model baseline", "hadronic",
         "examples/extended/hadronic/Hadr02", "Hadr02", "hadr02.in"},
        {"opnovice2", "OpNovice2 optical photon transport", "optical",
         "examples/extended/optical/OpNovice2", "OpNovice2", "electron.mac"},
        {"par01", "Par01 fast-simulation parameterisation", "parameterisation",
         "examples/extended/parameterisations/Par01", "examplePar01",
         "examplePar01.in"},
    };
}

inline const CanonicalExampleSpec& CanonicalExampleByName(const std::string& name) {
    static const auto examples = AllCanonicalExamples();
    for (const auto& example : examples) {
        if (example.name == name) {
            return example;
        }
    }
    throw std::invalid_argument("unknown canonical Geant4 example: " + name);
}

inline std::filesystem::path CanonicalLogPath(const CanonicalExampleSpec& example,
                                              const std::string& commit) {
    return std::filesystem::path("benchmarks") / "results" / "canonical" /
           (example.name + "_" + commit + ".log");
}

}  // namespace g4gpu::benchmarks
