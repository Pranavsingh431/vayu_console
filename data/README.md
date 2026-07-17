# Data

**`raw/` is immutable.** Never edit, never overwrite. Every processed artefact must be
reproducible from `raw/` alone — that is the whole point of keeping it.

| Directory    | Contents                         | Safe to delete?                              |
| ------------ | -------------------------------- | -------------------------------------------- |
| `raw/`       | Exactly what the source returned | **No** — re-downloading may not reproduce it |
| `processed/` | Derived from `raw/`              | Yes — rebuildable                            |
| `cache/`     | Transient fetch cache            | Yes                                          |

If something in `processed/` cannot be rebuilt from `raw/`, it is not derived. It is
precious, and it is in the wrong directory.

Contents are gitignored: this is data, not source.
