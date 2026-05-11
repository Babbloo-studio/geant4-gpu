#include "BenchmarkDriver.hh"

int main(int argc, char** argv) {
    return g4gpu::benchmarks::RunBenchmarkDriver(
        g4gpu::benchmarks::BenchmarkEventByName("cosmic_shower"), argc, argv);
}
