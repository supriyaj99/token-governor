# TokenGovernor — Benchmark Results

Reproducible output of `python -m benchmark.run_benchmark` (fixed seed).
Numbers come from the offline simulator in `app/simulate.py`; with real
models (MOCK_MODE=false) the same router logic drives real API calls.

```
TokenGovernor benchmark — 6000 requests, quality bar = 0.7, seed = 7
(reproducible: same seed => same numbers)

policy            total_cost($)  quality_pass  vs_full_cost
-----------------------------------------------------------
always_full             17.7704        97.2%         +0.0%
always_nano              1.0662        42.1%        +94.0%
random                   8.5756        73.0%        +51.7%
static_rules             9.6381        93.0%        +45.8%
ORACLE(best)             8.4943        88.7%        +52.2%
LEARNING(ours)           9.3857        90.9%        +47.2%

HEADLINE (learning router vs always-full):
  47.2% cheaper, quality 90.9% vs 97.2% (within 6.2 points of the quality ceiling)

Cost / quality trade-off (higher confidence = more quality, less savings):
  confidence     cost($)   quality   savings_vs_full
        0.30      6.6921    76.0%            62.3%
        0.45      9.1125    90.1%            48.7%
        0.60      9.3857    90.9%            47.2%
        0.75      9.6255    92.0%            45.8%
        0.90     11.3779    94.2%            36.0%

Learning curve (per 500-request window):
   after_n  window_cost($)  window_quality
       500           0.716          83.4%
      1000           0.696          90.4%
      1500           0.792          90.2%
      2000           0.783          91.4%
      2500           0.828          90.4%
      3000           0.717          91.4%
      3500           0.790          92.8%
      4000           0.768          91.4%
      4500           0.869          91.8%
      5000           0.829          92.6%
      5500           0.779          92.2%
      6000           0.820          92.8%

Oracle (best possible) cost was $8.4943 at 88.7% quality — the ceiling our router approaches.
```
