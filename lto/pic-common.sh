# Shared PIC/BS-SOLCTRA launch helpers for the LTO comparison. Sourced by the
# job and smoke scripts; expects SLURM_NTASKS / SLURM_NNODES in the environment.
TOTAL_STEPS=100
GRID=1000

marker() {
  local line="### code=$1 lang=$2 lto=$3 scaling=$4 style=$5 rep=$6"
  echo "$line"; echo "$line" >&2
}

# pic_c BIN LTO SCALING STYLE REP NPARTICLES
pic_c() {
  local bin=$1 lto=$2 scaling=$3 style=$4 rep=$5 np=$6
  local args
  case $style in
    GEOMETRIC)  args="1 2 GEOMETRIC 0.99" ;;
    SINUSOIDAL) args="0 1 SINUSOIDAL" ;;
    LINEAR)     args="1 0 LINEAR 1.0 3.0" ;;
    PATCH)      args="1 0 PATCH 0 200 100 200" ;;
  esac
  marker pic c "$lto" "$scaling" "$style" "$rep"
  mpirun -n "${SLURM_NTASKS}" "./$bin" "${TOTAL_STEPS}" "${GRID}" "${np}" $args
}

# pic_rust BIN LTO SCALING STYLE REP NPARTICLES
pic_rust() {
  local bin=$1 lto=$2 scaling=$3 style=$4 rep=$5 np=$6
  local args
  case $style in
    GEOMETRIC)  args="-p 1 -v 2 geometric -a 0.99" ;;
    SINUSOIDAL) args="-p 0 -v 1 sinusoidal" ;;
    LINEAR)     args="-p 1 -v 0 linear -n 1.0 -c 3.0" ;;
    PATCH)      args="-p 1 -v 0 patch --xleft 0 --xright 200 --ybottom 100 --ytop 200" ;;
  esac
  marker pic rust "$lto" "$scaling" "$style" "$rep"
  mpirun -n "${SLURM_NTASKS}" "./$bin" -i "${TOTAL_STEPS}" -g "${GRID}" -t "${np}" $args
}

# pic_all_variants SCALING STYLE REP NPARTICLES: the four binaries back to back
pic_all_variants() {
  local scaling=$1 style=$2 rep=$3 np=$4
  pic_c    pic         0 "$scaling" "$style" "$rep" "$np"
  pic_c    pic-lto     1 "$scaling" "$style" "$rep" "$np"
  pic_rust pic-mpi     0 "$scaling" "$style" "$rep" "$np"
  pic_rust pic-mpi-lto 1 "$scaling" "$style" "$rep" "$np"
}

# solctra_c BIN LTO REP NPARTICLES STEPS
solctra_c() {
  local bin=$1 lto=$2 rep=$3 np=$4 steps=$5
  marker solctra c "$lto" strong NA "$rep"
  OMP_NUM_THREADS=${SLURM_NTASKS_PER_NODE} OMP_SCHEDULE=dynamic \
  srun -n "${SLURM_NNODES}" "./$bin" \
    -length "${np}" \
    -particles input_big.txt \
    -id "${SLURM_JOB_ID}${lto}${rep}" \
    -resource resources/ \
    -mode 1 \
    -magnetic_prof 0 100 0 2 \
    -print_typef 1 \
    -steps "${steps}"
}

# solctra_rust BIN LTO REP NPARTICLES STEPS
solctra_rust() {
  local bin=$1 lto=$2 rep=$3 np=$4 steps=$5
  marker solctra rust "$lto" strong NA "$rep"
  RAYON_NUM_THREADS=${SLURM_NTASKS_PER_NODE} RUST_LOG=info \
  srun -n "${SLURM_NNODES}" "./$bin" \
    --num-particles "${np}" \
    --particles-file input_big.csv \
    --resource-path resources-rs/ \
    --mode 1 \
    --magprof 0 \
    --steps "${steps}" \
    -w 10000 \
    --output "results_rs${SLURM_JOB_ID}${lto}${rep}"
}

solctra_all_variants() {
  local rep=$1 np=$2 steps=$3
  solctra_c    bs-solctra-multinode     0 "$rep" "$np" "$steps"
  solctra_c    bs-solctra-multinode-lto 1 "$rep" "$np" "$steps"
  solctra_rust bs-solctra-rs            0 "$rep" "$np" "$steps"
  solctra_rust bs-solctra-rs-lto        1 "$rep" "$np" "$steps"
}
