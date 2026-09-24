#!/bin/bash
# Build the eight LTO-comparison binaries (C/C++ and Rust, with and without LTO).
# Must run on a kura compute node (srun); the login node has a different glibc.
set -eu
. /opt/Modules/3.2.10/init/sh
module purge
module load mpich/3.3.2-gcc-9.3.0 gcc/9.3.0
export LIBCLANG_PATH=/data/casch/tools/envs/clang/lib
export PATH=$HOME/.cargo/bin:$PATH
ROOT=/work/casch/RustMPIExperiments
LTO=$ROOT/lto
BIN=$LTO/bin
ORIG=$LTO/orig-binaries-2025
mkdir -p "$BIN" "$ORIG"

echo "### host: $(hostname)"
which gcc mpicc mpicxx cargo
gcc --version | head -1
cargo +1.85.0 --version
rustc +1.85.0 --version

# Keep the binaries the 2025 runs used; the in-tree rebuilds below overwrite them.
cp -pn "$ROOT/Kernels/MPI1/PIC-static/pic" "$ORIG/pic" || true
cp -pn "$ROOT/Kernels/RUST/pic-mpi/target/release/pic-mpi" "$ORIG/pic-mpi" || true
cp -pn "$ROOT/bs-solctra-mpi-rs/target/release/bs-solctra-rs" "$ORIG/bs-solctra-rs" || true
cp -pn "$ROOT/bs-solctra-implementations/results/bs-solctra-multinode" "$ORIG/bs-solctra-multinode" || true

echo "### C++ BS-SOLCTRA"
cd "$ROOT/bs-solctra-implementations"
SRC="solctra_multinode.h solctra_multinode.cpp main_multinode.cpp utils.h utils.cpp"
rm -f ./*.gch
mpicxx -O3 -std=c++11 -fopenmp -o "$BIN/bs-solctra-multinode" $SRC
rm -f ./*.gch
mpicxx -v -O3 -std=c++11 -fopenmp -flto -o "$BIN/bs-solctra-multinode-lto" $SRC 2> "$LTO/build-cxx-lto.verbose"
rm -f ./*.gch
echo "cxx lto-wrapper/lto1 lines: $(grep -c 'lto-wrapper\|lto1' "$LTO/build-cxx-lto.verbose" || true)"

echo "### C PIC"
cd "$ROOT/Kernels/MPI1/PIC-static"
make clean >/dev/null 2>&1 || true
rm -f ./*.o pic
make pic OPTFLAGS="-O3 -mtune=native -ffast-math -g3 -Wall -flto" LIBS="-lm -v" 2> "$LTO/build-c-lto.verbose"
cp -p pic "$BIN/pic-lto"
echo "c lto-wrapper/lto1 lines: $(grep -c 'lto-wrapper\|lto1' "$LTO/build-c-lto.verbose" || true)"
make clean >/dev/null 2>&1 || true
rm -f ./*.o pic
make pic OPTFLAGS="-O3 -mtune=native -ffast-math -g3 -Wall"
cp -p pic "$BIN/pic"

echo "### Rust"
for t in "$ROOT/Kernels/RUST/pic-mpi/Cargo.toml" "$ROOT/bs-solctra-mpi-rs/Cargo.toml"; do
  grep -q 'profile.release-lto' "$t" || printf '\n[profile.release-lto]\ninherits = "release"\nlto = "fat"\n' >> "$t"
done

cd "$ROOT/Kernels/RUST/pic-mpi"
cargo +1.85.0 build --release -v > "$LTO/build-pic-rs.log" 2>&1
cargo +1.85.0 build --profile release-lto -v > "$LTO/build-pic-rs-lto.log" 2>&1
cp -p target/release/pic-mpi "$BIN/pic-mpi"
cp -p target/release-lto/pic-mpi "$BIN/pic-mpi-lto"

cd "$ROOT/bs-solctra-mpi-rs"
cargo +1.85.0 build --release -v > "$LTO/build-solctra-rs.log" 2>&1
cargo +1.85.0 build --profile release-lto -v > "$LTO/build-solctra-rs-lto.log" 2>&1
cp -p target/release/bs-solctra-rs "$BIN/bs-solctra-rs"
cp -p target/release-lto/bs-solctra-rs "$BIN/bs-solctra-rs-lto"

echo "### LTO flag check in cargo -v logs (crate-name lines with -C lto=fat)"
for l in build-pic-rs build-pic-rs-lto build-solctra-rs build-solctra-rs-lto; do
  n=$(grep -c 'crate-name.*-C lto=fat' "$LTO/$l.log" || true)
  echo "$l: $n"
done
grep -o 'crate-name pic_mpi .*' "$LTO/build-pic-rs-lto.log" | tr ' ' '\n' | grep -i 'lto\|opt-level\|codegen-units\|target-cpu' || true
grep -o 'crate-name bs_solctra_rs .*' "$LTO/build-solctra-rs-lto.log" | tr ' ' '\n' | grep -i 'lto\|opt-level\|codegen-units\|target-cpu' || true

echo "### binaries"
ls -la "$BIN"
md5sum "$BIN"/*
