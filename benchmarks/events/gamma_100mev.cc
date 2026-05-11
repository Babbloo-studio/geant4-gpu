#include "BenchmarkDriver.hh"

int main(int argc, char** argv) {
    return g4gpu::benchmarks::RunBenchmarkDriver(
        g4gpu::benchmarks::BenchmarkEventByName("gamma_100mev"), argc, argv);
}
