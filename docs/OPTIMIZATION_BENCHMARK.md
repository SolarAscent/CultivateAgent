# MOBO Backend Benchmark

Synthetic benchmark only; real objective values must come from wet-lab `tell()` calls. Settings: seeds=[0, 1, 2], rounds=3, batch=3, pool_size=96.

The `botorch` backend is legacy qNEHVI. The `botorch-log` backend uses `qLogNoisyExpectedHypervolumeImprovement`, the numerically improved variant recommended by BoTorch when available.

## Per-Seed Results

| seed | backend | start_hv | final_hv | delta_hv | normalized_final_hv |
| --- | --- | --- | --- | --- | --- |
| 0 | q-ParEGO | 8.423 | 17.552 | 9.129 | 0.996 |
| 0 | qNEHVI | 8.423 | 17.623 | 9.2 | 1.0 |
| 0 | qLogNEHVI | 8.423 | 17.623 | 9.2 | 1.0 |
| 1 | q-ParEGO | 6.743 | 10.329 | 3.586 | 0.776 |
| 1 | qNEHVI | 6.743 | 13.31 | 6.567 | 1.0 |
| 1 | qLogNEHVI | 6.743 | 13.31 | 6.567 | 1.0 |
| 2 | q-ParEGO | 3.843 | 8.547 | 4.704 | 1.0 |
| 2 | qNEHVI | 3.843 | 7.591 | 3.748 | 0.888 |
| 2 | qLogNEHVI | 3.843 | 7.591 | 3.748 | 0.888 |

## Summary

| backend | mean_normalized_final_hv | n_seeds |
| --- | --- | --- |
| q-ParEGO | 0.924 | 3 |
| qLogNEHVI | 0.963 | 3 |
| qNEHVI | 0.963 | 3 |
