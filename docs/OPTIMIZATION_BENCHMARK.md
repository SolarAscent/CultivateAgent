# MOBO Backend Benchmark

Synthetic benchmark only; real objective values must come from wet-lab `tell()` calls. Settings: seeds=[0, 1, 2], rounds=3, batch=3, pool_size=96.

BoTorch 0.18.1 warns that legacy `qNoisyExpectedHypervolumeImprovement` has numerical issues and recommends `qLogNoisyExpectedHypervolumeImprovement`; this project still labels the path qNEHVI because that is the implemented acquisition today.

## Per-Seed Results

| seed | backend | start_hv | final_hv | delta_hv | normalized_final_hv |
| --- | --- | --- | --- | --- | --- |
| 0 | q-ParEGO | 8.423 | 17.552 | 9.129 | 1.0 |
| 0 | qNEHVI | 8.423 | 17.52 | 9.097 | 0.998 |
| 1 | q-ParEGO | 6.743 | 10.329 | 3.586 | 0.776 |
| 1 | qNEHVI | 6.743 | 13.31 | 6.567 | 1.0 |
| 2 | q-ParEGO | 3.843 | 8.547 | 4.704 | 0.896 |
| 2 | qNEHVI | 3.843 | 9.534 | 5.691 | 1.0 |

## Summary

| backend | mean_normalized_final_hv | n_seeds |
| --- | --- | --- |
| q-ParEGO | 0.891 | 3 |
| qNEHVI | 0.999 | 3 |
