#!/bin/sh

export OUT_DIR=weak_runs_log/
tar -cvzf output_weak_scaling.tar.gz std* data.csv ${OUT_DIR}
