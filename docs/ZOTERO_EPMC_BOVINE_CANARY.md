# Europe PMC Bovine JATS Canary

Status: **source verification only; no canonical corpus entry or evidence approval**.

The canary tests whether selected bovine-focused candidates resolve to the expected
DOI/title, identify as a research article, declare a recognized Creative Commons
license inside JATS, and contain parseable table structure. Biological scope hints
remain unadjudicated.

## Verification Result

| Status | Rows |
|---|---:|
| `verified` | 10 |

| Selection role | Verified rows |
|---|---:|
| `bovine_expansion_context` | 3 |
| `direct_medium_primary` | 7 |

- Requests used in this invocation: 0
- Checkpoints reused in this invocation: 10
- Total JATS tables: 25
- Total JATS cells: 996
- Cells with statistical notation: 58
- Table-bearing JATS: 8/10
- JATS with statistical-notation cells: 3/10

## Integrity

- Canary manifest SHA-256: `6dd9e0d6e7c2b8d34da4843172852084302678c230cbf8d68add595ad6888fde`
- OA audit SHA-256: `4a2eb46365f3fb75721456a3012aff1ee003901090f0ff0a4d9ddef67b5d6255`
- Verification TSV SHA-256: `ac0877a5500c006bd96196ff322eb0ce20e9cad0735da8dc999f0e863b5647eb`
- XML checkpoints are local, ignored artifacts; each committed row retains the
  verified source SHA-256 and contains no source text or numeric result.
- `verified` means acquisition-ready only. It does not mean bovine-scope approved,
  quantitatively extractable, human-reviewed, or wet-lab ready.
