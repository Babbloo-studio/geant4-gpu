#include "BenchmarkDriver.hh"

int main(int argc, char** argv) {
    return g4gpu::benchmarks::RunBenchmarkDriver(
        g4gpu::benchmarks::BenchmarkEventByName("nbar_carbon"), argc, argv);
}
