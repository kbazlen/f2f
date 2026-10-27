# Fire-to-Faucet Review

## Configure paths

All data paths are set in `scripts/configs.py`:

- Benchmark dataset: `DATA_DIR` (default: `../data/f2f_benchmark_v1.0.0-rc2`). The individual parquet paths are built from it.
- State shapefile: `STATE_SHAPEFILE` (default: `data/cb_2018_us_state_500k 2/cb_2018_us_state_500k.shp`).
- Render output: pass `--output-dir` to the Quarto command. Use `../outputs` to keep generated files outside this folder.

The benchmark dataset must be available at the configured `DATA_DIR` before rendering. The state shapefile is included in the repository.

## Render

From this folder, run:

```sh
quarto render f2f_review.qmd --to html --output-dir ../outputs
```

For live preview, run:

```sh
quarto preview f2f_review.qmd --output-dir ../outputs
```

To render PDF (requires a LaTeX installation), run:

```sh
quarto render f2f_review.qmd --to pdf --output-dir ../outputs
```