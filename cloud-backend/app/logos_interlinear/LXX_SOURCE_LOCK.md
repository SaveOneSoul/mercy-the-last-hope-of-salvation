# LXX / Septuagint Source Lock

This gate locks the Catholic Old Testament Greek source layer before any bulk Septuagint import is allowed.

## Pinned upstream

- Repository: `OpenGreekAndLatin/First1KGreek`
- Commit: `8ee111eb44ecef4120c844e10749178d95d1f30c`
- Licence: **CC BY-SA 4.0**
- Canonical lock: `lxx-swete-inventory.json`
- Importer: `scripts/vendor_swete_lxx.py`

The source layer remains physically and logically separable from corpora under different licence terms. Each approved source unit is locked by exact repository path and Git blob SHA-1. When vendoring is eventually enabled, the importer re-computes the Git blob hash, parses the XML, and records a SHA-256 checksum for the downloaded bytes.

## Lock status

The lock is intentionally **incomplete**: **47 of 48 required source units are verified and checksum-locked**.

The blocker is **Ecclesiastes (`tlg030`)**. At the pinned First1KGreek commit, the directory has CTS metadata but no Greek text XML to lock. The metadata advertises `opp-grc2` and describes Hart 1909 rather than an eligible Swete text. Because there is no source file, there is no truthful path/checksum to record.

Therefore:

- `lock_complete` remains `false`.
- `first1kgreek-swete.production_import_allowed` remains `false`.
- `first1kgreek-swete.source_inventory_verified` remains `false`.
- `scripts/vendor_swete_lxx.py` refuses to write a production Greek OT corpus.
- CI may validate the lock with `--check-lock`, but it cannot bypass the blocker.

This is deliberate. Do not fill Ecclesiastes from an arbitrary website or silently switch editions.

## Catholic mapping decisions

The lock treats the deuterocanonical books as normal canonical material. Special mappings are explicit:

- **Ezra + Nehemiah** use First1K `tlg018` (Esdras B) as a shared Greek source; a reviewed versification map must split the two canonical books downstream.
- **Esther** uses `tlg019`; Greek additions must remain explicit in Catholic versification alignment.
- **Baruch** uses `tlg050` plus `tlg052`, with the Letter of Jeremiah mapped to Catholic Baruch 6.
- **Daniel** uses the Theodotion lane `tlg057`, `tlg058`, and `tlg059` for the primary Catholic Greek witness, including Susanna and Bel and the Dragon.
- **Sirach** deliberately selects `tlg034.1st1K-grc2`, which First1K CTS metadata identifies as Swete. The Hart 1909 `grc1` edition is excluded.
- **Isaiah** deliberately selects `tlg048.1st1K-grc1`, which First1K CTS metadata identifies as Swete. The Ottley 1904 `grc2` edition is excluded.

Old Greek Daniel (`tlg054`–`tlg056`) is retained as a possible future alternate witness, not part of the primary production lock.

## Activation rule

The Greek Catholic OT importer may be activated only after an exact reusable Ecclesiastes source is approved and pinned with:

1. edition/provenance evidence,
2. compatible licence,
3. immutable upstream revision,
4. exact source path,
5. integrity checksum,
6. explicit Catholic versification mapping.

Prefer an upstream First1KGreek correction or another independently verified source added as its own provenance layer. After that, update the inventory and source manifest together; the validators are designed to reject premature activation.

Run:

```bash
python tools/validate_logos_interlinear.py
python tools/validate_lxx_source_lock.py
python scripts/vendor_swete_lxx.py --check-lock
```

A normal `python scripts/vendor_swete_lxx.py` invocation will fail closed until `lock_complete` is true.
