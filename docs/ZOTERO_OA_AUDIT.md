# Zotero Open-Access Discovery Audit

Status: **discovery complete; no full text downloaded**.

Europe PMC and Crossref metadata identify candidates only. A candidate is not
authorized for corpus entry until the source DOI, in-document license, and file
structure pass the existing deterministic acquisition checks.

## Counts

| Status | Rows |
|---|---:|
| `crossref_cc_vor_candidate` | 34 |
| `epmc_jats_candidate` | 75 |
| `metadata_only_license_unverified` | 96 |
| `missing_doi` | 7 |

## Integrity

- Input: `data/literature/zotero_acquire_actionable.tsv`; SHA-256 `d78eb3253755ebd4b9c0b0e2bab209236e8f376bcafb1044c2664e56972257ac`
- Output: `data/literature/zotero_oa_audit.tsv`; SHA-256 `4a2eb46365f3fb75721456a3012aff1ee003901090f0ff0a4d9ddef67b5d6255`
- Requests used in this invocation: 0
- Checkpoints reused in this invocation: 410
- Crossref Creative Commons metadata is treated as a lead, not source-level proof.
- Europe PMC rows still require fullTextXML DOI/license/structure verification.

## Method Boundary

- Europe PMC DOI search and `fullTextXML` are documented by the
  [Europe PMC REST service](https://europepmc.org/RestfulWebService).
- Crossref supports DOI work lookup plus deposited license and full-text-link
  fields through its [REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/).
- OpenAlex was not used because its current API requires a key. No provider key
  or language model was needed for this deterministic audit.
- A public metadata record can be incomplete or stale. The 109 candidates are
  ordered acquisition leads, not permission findings and not evidence records.
