#!/usr/bin/env bash
# Particle dumps for the three PIC figures that show what the kernel computes.
#
# All three are small diagnostic runs; the rates they print mean nothing.
set -euo pipefail

RUST_PIC=${RUST_PIC:-../Kernels/RUST/pic-mpi/target/release/pic-mpi}
C_PIC=${C_PIC:-../Kernels/MPI1/PIC-static/pic}
OUT=${OUT:-data/pic_scene}

rm -rf "$OUT"
mkdir -p "$OUT/tracks" "$OUT/tiles" "$OUT/validation"

# 1. Tracks over a mesh small enough to draw the individual charges.
echo "== tracks"
"$RUST_PIC" -i 16 -g 24 -t 24 -p 1 -v 2 \
  --particle-dump "$OUT/tracks/t" --dump-every 1 \
  geometric -a 0.9 | grep -E "placed|validates"

# 2. Rank tiles and the particles crossing them, at the grid the experiments use.
echo "== tiles"
mpirun -n 8 "$RUST_PIC" -i 100 -g 1000 -t 2048 -p 0 -v 1 \
  --particle-dump "$OUT/tiles/p" --dump-every 1 \
  sinusoidal | grep -E "placed|validates"

# 3. Analytical validation, both implementations, every style. The grid is
#    smaller than the experiments' 1000 so that trajectories wrap inside the
#    plotted window; the check itself is unchanged, and holds at 1000 too.
echo "== validation"
validate() {
  style=$1; rust_args=$2; c_args=$3
  eval "\"$RUST_PIC\" -i 200 -g 200 -t 1500 --particle-dump \"$OUT/validation/rust-$style\" --dump-every 2 $rust_args" \
    | grep -E "validates"
  ( export PRK_PARTICLE_DUMP="$OUT/validation/c-$style" PRK_DUMP_EVERY=2
    eval "\"$C_PIC\" 200 200 1500 $c_args" | grep -E "validates" )
}
validate geometric  "-p 1 -v 2 geometric -a 0.99"                                    "1 2 GEOMETRIC 0.99"
validate sinusoidal "-p 0 -v 1 sinusoidal"                                            "0 1 SINUSOIDAL"
validate linear     "-p 1 -v 0 linear -n 1.0 -c 3.0"                                  "1 0 LINEAR 1.0 3.0"
validate patch      "-p 1 -v 0 patch --xleft 0 --xright 40 --ybottom 20 --ytop 40"    "1 0 PATCH 0 40 20 40"

echo "PIC SCENE DONE"
