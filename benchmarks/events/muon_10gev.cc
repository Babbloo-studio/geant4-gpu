#include "BenchmarkDriver.hh"

int main(int argc, char** argv) {
    return g4gpu::benchmarks::RunBenchmarkDriver(
        g4gpu::benchmarks::BenchmarkEventByName("muon_10gev"), argc, argv);
}
