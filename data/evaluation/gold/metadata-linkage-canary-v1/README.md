# Metadata Linkage Canary v1

Status: frozen before the first live model call.

This canary tests a narrow metadata-QA task motivated by the repository's prior
cross-paper source-identity mixing failure. Each item combines the canonical
title of one identity-verified bovine paper with either its own Zotero abstract
or another same-domain paper's real abstract. DeepSeek may return only item and
field pointers for suspected mismatches; it never returns replacement metadata.

The spec stores no abstract text. The runner resolves titles and DOI-keyed
abstracts deterministically from the canonical corpus manifest and the owner's
Zotero CSV, verifies DOI/title identity, chooses the longest normalized abstract
with a lexical tie-break for duplicate export variants, and hashes each exact input. Six items are
matched and six are deliberately cross-linked. The task passes only if all
three temperature-zero repeats meet recall >= 0.95 and precision >= 0.75, all
responses pass the strict schema, and pairwise selection Jaccard is >= 0.95.
Flagging every item therefore fails the precision/work-reduction gate.

This is a capability canary, not scientific evidence and not authorization to
correct metadata automatically. A passing result permits only a bounded shadow
run whose candidates still require deterministic or human confirmation.
