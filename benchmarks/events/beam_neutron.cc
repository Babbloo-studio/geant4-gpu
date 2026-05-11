#include "BenchmarkDriver.hh"

int main(int argc, char** argv) {
    return g4gpu::benchmarks::RunBenchmarkDriver(
        g4gpu::benchmarks::BenchmarkEventByName("beam_neutron"), argc, argv);
}
