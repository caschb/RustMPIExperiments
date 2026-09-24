# BS-SOLCTRA visualisations

Figures of what BS-SOLCTRA actually computes, for the CLEI 2026 talk in
`../../rust-hpc-presentation`. The scaling plots already in the deck show how
fast the codes run; these show the physics they produce.

## What it draws

| Figure | Shows |
|--------|-------|
| `solctra_fieldlines.png` | The twelve SCR-1 modular coils in 3D with traced field lines through them, coloured by the magnetic field magnitude. |
| `solctra_poincare.pdf` | Poincaré section at a fixed toroidal angle: nested closed curves are intact flux surfaces. |
| `solctra_confinement.pdf` | Arc length each line is traced before leaving the containment region, against where it started. |
| `pic_migration.pdf` | Particles the PIC ranks hand to their neighbours per timestep, for the four initialization styles. |
| `pic_migration_mape.pdf` | That migration rate against the reported MAPE, one point per style and scaling mode. |
| `pic_model.pdf` | The charge mesh, the four charges acting on one particle, and particle tracks over the mesh. |
| `pic_tiles.pdf` | Rank tiles drawn explicitly, with the particles that changed owner during a step ringed. |
| `pic_validation.pdf` | Simulated against closed-form position, C and Rust overlaid, with the deviation. |

## Running it

Both Rust codes have to be built first:

```
cd ../bs-solctra-mpi-rs      && cargo build --release
cd ../Kernels/RUST/pic-mpi   && cargo build --release
```

Then, from this directory:

```
make          # trace, then render everything
make figures  # re-render from data already traced
make install  # copy the figures into the deck's figures/ directory
```

`make trace-poincare` is the slow one, a couple of minutes for 32 lines of
400 000 steps. The other two are seconds. `RANKS` and `THREADS` control the MPI
ranks and the Rayon threads per rank.

## Where the data comes from

The simulation grew a `--diagnostics` mode for this. It is a separate traversal
from `simulate_particles`, which is the function the scaling experiments
measure, so recording samples cannot show up in those timings. In that mode each
rank writes three files:

| File | Contents |
|------|----------|
| `trajectory_<rank>.csv` | `line_id, step, x, y, z, b_magnitude`, sampled every `-w` steps |
| `poincare_<rank>.csv` | `line_id, turn, r, z`, one row per crossing of the section plane |
| `fieldlines_<rank>.csv` | one row per line: starting point, normalised minor radius, steps traced, crossings, and the step at which it was lost |

Crossings are found by interpolating between consecutive steps, and only
counted in one direction, so each toroidal transit contributes one point.

The coil geometry is not written out; the figures read the twelve
`Bobina*.csv` resource files the simulation itself reads.

## Starting points

The `input_1000.csv` shipped with the code is a grid over eleven toroidal
angles, which is what a scaling benchmark wants and not what a Poincaré section
wants. `viz starts` writes a radial ray at the section plane instead, one line
per flux surface:

```
uv run viz starts --out data/starts.csv --count 32 --r-min 0.195 --r-max 0.312
```

Outside roughly `R = 0.192 .. 0.313` the lines leave the containment region
within a fraction of a turn, so a scan wider than that is only useful for the
confinement figure.

## PIC migration

`pic-mpi` grew a `--migration-log <PATH>` flag. Each rank records, per step, how
many particles it held and how many it enqueued for its eight neighbours,
reusing the `send_size` array the size exchange already builds, and writes
`<PATH>_<rank>.csv` after the timer has stopped. A run with the flag set is a
diagnostic run; its reported rate is not a measurement of anything.

`sweep_pic.sh` runs all four styles at both problem sizes over the rank counts
of the scaling experiments, taking the parameters from `Workbook.org`. Since
`srun -n ${SLURM_NNODES}` puts one rank per node, the cluster configurations
are 1 to 12 ranks and reproduce exactly on a laptop. `make summary` prints the
table behind the figures.

Two things the measurement turned up, both visible in the figures:

- With Patch at 8 ranks, rank 0 holds every particle and the other seven hold
  none, for 98 of the 100 steps. Patch is not merely imbalanced, it is
  single-rank with idle neighbours.
- The four styles differ in initial vertical velocity as well as in spatial
  distribution (`-v 2`, `-v 1`, `-v 0`, `-v 0`). At two ranks the grid splits in
  y only, so Linear and Patch, which start with no vertical velocity, migrate
  nothing at all.

## What PIC computes, and the analytical check

`--particle-dump <PATH>` on the Rust code, and `PRK_PARTICLE_DUMP` on the C
code, record particle state every `--dump-every` (`PRK_DUMP_EVERY`) steps into
`<PATH>_<rank>.csv`, alongside the rank's tile bounds in
`<PATH>_tiles_<rank>.csv`. The C side is driven by the environment rather than
argv so the positional argument list the experiments use is untouched. Both
record before the move, so `step` counts moves already applied and lines up
with `verify_particle`.

`sweep_pic_scene.sh` produces all three datasets. The validation runs use a
grid of 200 rather than the experiments' 1000, only so trajectories wrap inside
the plotted window; the check is the same and also holds at 1000.

The result is stronger than the deck claims. Over 1 258 476 sampled positions,
across all four initialization styles and both languages, the simulated
position equals the closed form **exactly** rather than within the 1e-6
tolerance `verify_particle` applies. C and Rust also agree with each other bit
for bit.
