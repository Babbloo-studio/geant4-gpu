#include <cassert>
#include <iostream>

#include "g4gpu/G4GPUHitBuffer.hh"
#include "g4gpu/G4GPUTrackBuffer.hh"

int main() {
    constexpr int n = 1024;
    g4gpu::G4GPUTrackBuffer buffer(n);

    auto& host = buffer.host();
    assert(host.capacity == n);
    host.size = n;
    for (int i = 0; i < n; ++i) {
        host.x[i] = static_cast<float>(i);
        host.y[i] = 0.0f;
        host.z[i] = 0.0f;
        host.dx[i] = 0.0f;
        host.dy[i] = 0.0f;
        host.dz[i] = 1.0f;
        host.ekin[i] = 1000.0f;
        host.time[i] = 0.0f;
        host.pdg[i] = 13;
        host.material_idx[i] = 0;
        host.volume_idx[i] = 0;
        host.track_id[i] = i + 1;
        host.parent_id[i] = 0;
        host.status[i] = 0;
    }

    buffer.copyHostToDevice();
    g4gpu::LaunchNullStepKernel(buffer.device().status, n);
    buffer.copyDeviceToHost();

    for (int i = 0; i < n; ++i) {
        if (host.status[i] != 1) {
            std::cerr << "FAIL: status[" << i << "]=" << host.status[i] << '\n';
            return 1;
        }
    }

    std::cout << "PASS\n";
    return 0;
}
