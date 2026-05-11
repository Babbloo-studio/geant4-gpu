#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>

#include "g4gpu/NeutronStepKernel.hh"

namespace {

void Fail(const std::string& message) {
    std::cerr << "FAIL: " << message << '\n';
    std::exit(1);
}

void ExpectNear(double observed, double expected, double tolerance,
                const std::string& label) {
    if (std::abs(observed - expected) > tolerance) {
        Fail(label + " observed=" + std::to_string(observed) +
             " expected=" + std::to_string(expected));
    }
}

void ExpectOk(const g4gpu::NeutronElasticResult& result, const std::string& label) {
    if (result.status != g4gpu::NeutronElasticStatus::ok) {
        Fail(label + " returned non-ok status");
    }
}

void CheckForwardBackward(double A) {
    const double alpha = ((A - 1.0) / (A + 1.0)) * ((A - 1.0) / (A + 1.0));
    const auto forward = g4gpu::ComputeNeutronElasticKinematics(100.0f, static_cast<float>(A), 1.0f);
    const auto backward = g4gpu::ComputeNeutronElasticKinematics(100.0f, static_cast<float>(A), -1.0f);
    ExpectOk(forward, "forward scatter");
    ExpectOk(backward, "backward scatter");
    ExpectNear(forward.energy_fraction, 1.0, 1.0e-6, "forward energy fraction");
    ExpectNear(backward.energy_fraction, alpha, 1.0e-6, "backward energy fraction");
    ExpectNear(forward.outgoing_energy_mev, 100.0, 1.0e-4, "forward outgoing energy");
    ExpectNear(backward.outgoing_energy_mev, 100.0 * alpha, 1.0e-4,
               "backward outgoing energy");
}

void CheckMeanFraction(double A) {
    const float samples[] = {-1.0f, -0.8f, -0.6f, -0.4f, -0.2f, 0.0f,
                             0.2f, 0.4f, 0.6f, 0.8f, 1.0f};
    double mean = 0.0;
    for (const float c : samples) {
        const auto result = g4gpu::ComputeNeutronElasticKinematics(1.0f, static_cast<float>(A), c);
        ExpectOk(result, "sampled scatter");
        if (result.energy_fraction < -1.0e-6 || result.energy_fraction > 1.0 + 1.0e-6) {
            Fail("energy fraction outside [0, 1]");
        }
        mean += result.energy_fraction;
    }
    mean /= static_cast<double>(sizeof(samples) / sizeof(samples[0]));
    const double alpha = ((A - 1.0) / (A + 1.0)) * ((A - 1.0) / (A + 1.0));
    ExpectNear(mean, (1.0 + alpha) / 2.0, 1.0e-6, "mean energy fraction");
}

}  // namespace

int main() {
    CheckForwardBackward(1.0);   // hydrogen
    CheckForwardBackward(12.0);  // carbon
    CheckMeanFraction(1.0);
    CheckMeanFraction(12.0);

    const auto clamped_high = g4gpu::ComputeNeutronElasticKinematics(10.0f, 12.0f, 2.0f);
    const auto clamped_low = g4gpu::ComputeNeutronElasticKinematics(10.0f, 12.0f, -2.0f);
    ExpectOk(clamped_high, "high clamp");
    ExpectOk(clamped_low, "low clamp");
    ExpectNear(clamped_high.energy_fraction, 1.0, 1.0e-6, "clamped forward limit");
    ExpectNear(clamped_low.energy_fraction,
               ((12.0 - 1.0) / (12.0 + 1.0)) * ((12.0 - 1.0) / (12.0 + 1.0)),
               1.0e-6, "clamped backward limit");

    const auto invalid = g4gpu::ComputeNeutronElasticKinematics(10.0f, 0.0f, 0.0f);
    if (invalid.status != g4gpu::NeutronElasticStatus::invalid_target_mass_ratio ||
        invalid.energy_fraction != 0.0f || invalid.outgoing_energy_mev != 0.0f) {
        Fail("invalid A <= 0 was not rejected clearly");
    }

    const std::string notice = g4gpu::NeutronStepKernelScaffoldNotice();
    if (notice.find("no Geant4 neutron parity claim") == std::string::npos ||
        notice.find("no speed claim") == std::string::npos) {
        Fail("scaffold notice must reject parity and speed claims");
    }

    std::cout << "PASS: neutron elastic kinematics scaffold only; "
              << g4gpu::NeutronStepKernelScaffoldNotice() << '\n';
    return 0;
}
