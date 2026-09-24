RESOURCES ?= ../bs-solctra-mpi-rs/tests/test-resources/resources
SOLCTRA   ?= ../bs-solctra-mpi-rs/target/release/bs-solctra-rs
PIC       ?= ../Kernels/RUST/pic-mpi/target/release/pic-mpi
PIC_C     ?= ../Kernels/MPI1/PIC-static/pic
# The node counts the deck's MAPE table averages over.
NODES     ?= 1 2 4 6 8
RANKS     ?= 4
THREADS   ?= 3
SLIDES    ?= ../../rust-hpc-presentation/figures

UV   = uv
TRACE = RAYON_NUM_THREADS=$(THREADS) mpirun -n $(RANKS) $(SOLCTRA) --resource-path $(RESOURCES) --diagnostics

.PHONY: all figures trace clean install summary
.PHONY: trace-fieldlines trace-poincare trace-confinement trace-pic trace-pic-scene

all: trace figures

## Simulation runs. Each writes per-rank CSVs under data/.

trace: trace-fieldlines trace-poincare trace-confinement trace-pic trace-pic-scene

# Twelve lines, fifteen toroidal turns, sampled densely enough to draw as tubes.
trace-fieldlines:
	@mkdir -p data/fieldlines
	$(UV) run viz starts --out data/starts_3d.csv --count 12 --r-min 0.200 --r-max 0.305
	$(TRACE) --particles-file data/starts_3d.csv --output data/fieldlines \
	  --num-particles 12 --steps 24000 -w 6

# Long traces, ~255 crossings each. Sampling is switched off with a large -w,
# since only the plane crossings are needed. Takes a couple of minutes.
trace-poincare:
	@mkdir -p data/poincare
	$(UV) run viz starts --out data/starts_poincare.csv --count 32 --r-min 0.195 --r-max 0.312
	$(TRACE) --particles-file data/starts_poincare.csv --output data/poincare \
	  --num-particles 32 --steps 400000 -w 400000

# Wider radial span, to catch where lines stop being confined.
trace-confinement:
	@mkdir -p data/confinement
	$(UV) run viz starts --out data/starts_confinement.csv --count 44 --r-min 0.150 --r-max 0.332
	$(TRACE) --particles-file data/starts_confinement.csv --output data/confinement \
	  --num-particles 44 --steps 60000 -w 60000

# Every initialization style, at the rank counts and sizes of the scaling
# experiments. Migration depends on the algorithm, not the machine, so these
# reproduce the cluster configurations exactly.
trace-pic:
	PIC=$(PIC) ./sweep_pic.sh

# Small runs showing what the kernel computes: tracks over the charge mesh,
# rank tiles with the particles crossing them, and the analytical check for
# both implementations.
trace-pic-scene:
	RUST_PIC=$(PIC) C_PIC=$(PIC_C) ./sweep_pic_scene.sh

## Figures.

figures: figures/solctra_fieldlines.png figures/solctra_poincare.pdf \
         figures/solctra_confinement.pdf figures/pic_migration.pdf \
         figures/pic_migration_mape.pdf figures/pic_model.pdf \
         figures/pic_tiles.pdf figures/pic_validation.pdf

figures/solctra_fieldlines.png: data/fieldlines
	$(UV) run viz fieldlines --data data/fieldlines --resources $(RESOURCES) \
	  --out $@ --colour-by field --max-step 5000 --coil-opacity 0.6

figures/solctra_poincare.pdf: data/poincare
	$(UV) run viz poincare --data data/poincare --out $@

figures/solctra_confinement.pdf: data/confinement
	$(UV) run viz confinement --data data/confinement --out $@

figures/pic_migration.pdf: data/pic
	$(UV) run viz pic-migration --data data/pic --out $@ --ranks 8

figures/pic_migration_mape.pdf: data/pic
	$(UV) run viz pic-mape --data data/pic --out $@ --node-counts $(NODES)

figures/pic_model.pdf: data/pic_scene
	$(UV) run viz pic-model --data data/pic_scene/tracks --out $@

figures/pic_tiles.pdf: data/pic_scene
	$(UV) run viz pic-tiles --data data/pic_scene/tiles --out $@

figures/pic_validation.pdf: data/pic_scene
	$(UV) run viz pic-validation --data data/pic_scene/validation --out $@

# The table behind the two PIC figures.
summary:
	$(UV) run viz pic-summary --data data/pic --node-counts $(NODES)

install: figures
	@mkdir -p $(SLIDES)
	cp figures/solctra_fieldlines.png figures/solctra_poincare.pdf \
	   figures/solctra_confinement.pdf figures/pic_migration.pdf \
	   figures/pic_migration_mape.pdf figures/pic_model.pdf \
	   figures/pic_tiles.pdf figures/pic_validation.pdf $(SLIDES)/
	@echo "copied into $(SLIDES)"

clean:
	rm -rf figures data

# LTO on both sides: the follow-up to the deck's "LTO off" caveat. Input is
# parsed from the Kabré job outputs by ../lto/parse-results.py.
LTO_RESULTS ?= ../lto/results.csv
.PHONY: lto
lto: $(LTO_RESULTS)
	$(UV) run viz lto --results $(LTO_RESULTS) --out-dir figures
