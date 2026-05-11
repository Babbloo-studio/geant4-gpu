# Phase-5a benchmark stand-in geometries

The phase-5a drivers deliberately keep geometry local to the G4GPU side
project. They do not include or link against NNBAR production detector code.
Each geometry is a stripped-down stand-in for a canonical transport workload:

| Geometry ID | Workload | Stand-in |
| --- | --- | --- |
| `lead_block_1m3` | 100 MeV gamma EM shower | 1 m³ lead block |
| `mip_tunnel_10m` | 10 GeV muon MIP transport | 10 m straight detector stack |
| `carbon_12_target` | antinucleon-carbon signal channel | thin carbon-12 target |
| `cosmic_veto_stack` | cosmic-shower veto crossing | scintillator slab stack |
| `scintillator_cell` | optical scintillator photons | 10 cm scintillator cell |
| `b4c_beampipe` | thermal-neutron absorption | B4C absorber sleeve |

These fixtures are measurement-framework baselines, not physics claims. Later
validation phases can replace them with full Geant4/NNBAR geometry references
without crossing the G4GPU isolation boundary.
