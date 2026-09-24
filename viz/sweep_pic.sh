#!/usr/bin/env bash
# Record PIC particle migration for every initialization style, at the rank
# counts and problem sizes of the scaling experiments in Workbook.org.
#
# Migration is a property of the algorithm rather than of the machine, so these
# runs reproduce the cluster configurations exactly and can be done anywhere.
# They are diagnostic runs: the reported rates are meaningless here.
set -euo pipefail

PIC=${PIC:-../Kernels/RUST/pic-mpi/target/release/pic-mpi}
OUT=${OUT:-data/pic}
STEPS=${STEPS:-100}
GRID=${GRID:-1000}
PER_NODE=${PER_NODE:-102400}
STRONG_TOTAL=${STRONG_TOTAL:-$((12 * PER_NODE))}
RANKS=${RANKS:-"1 2 4 6 8 12"}

style_args() {
  case "$1" in
    geometric)  echo "-p 1 -v 2 geometric -a 0.99" ;;
    sinusoidal) echo "-p 0 -v 1 sinusoidal" ;;
    linear)     echo "-p 1 -v 0 linear -n 1.0 -c 3.0" ;;
    patch)      echo "-p 1 -v 0 patch --xleft 0 --xright 200 --ybottom 100 --ytop 200" ;;
    *) echo "unknown style $1" >&2; exit 1 ;;
  esac
}

for scaling in strong weak; do
  for style in geometric sinusoidal linear patch; do
    for n in $RANKS; do
      if [ "$scaling" = strong ]; then
        total=$STRONG_TOTAL
      else
        total=$((n * PER_NODE))
      fi
      dir="$OUT/$scaling/$style/r$n"
      mkdir -p "$dir"
      echo "== $scaling $style ranks=$n particles=$total"
      # shellcheck disable=SC2046
      mpirun -n "$n" "$PIC" -i "$STEPS" -g "$GRID" -t "$total" \
        --migration-log "$dir/mig" $(style_args "$style") \
        | grep -E "Solution|Rate" || true
    done
  done
done
echo "PIC SWEEP DONE"
