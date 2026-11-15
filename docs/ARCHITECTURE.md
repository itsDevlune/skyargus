# Architecture
One Django repository, with a compact apps/core application while product boundaries stabilize. Models, views, providers, exports, job tasks and native NEOSSat processing are separate modules; framework-independent numerical code lives in science/. This consciously avoids seven mostly empty Django apps. Split modules as functionality grows, without a microservice rewrite.

POST search validates → transaction creates Job + Dispatch → after-commit publication (Celery mode) → worker resolves archive metadata and bounded FITS → fixed-grid reprojection → atomic file writes → manifest transaction → status polling. Local Windows uses an explicitly isolated database-polling process, never Celery on Windows. Production Compose uses Celery/Redis/PostgreSQL. Redis carries job IDs. PostgreSQL/SQLite records are authoritative.

Public Sequence/Artifact objects are deduplicated by normalized selection and processing version. Private Candidate, Report and Job access uses server-side session ownership. Reports copy manifests and annotations and pin sequences through PROTECT references. Read grants use 256-bit random tokens stored only as SHA-256 hashes and can be revoked.

Remaining architecture work: immutable observation-version/contributor records, durable per-attempt records, global transactional quota reservations, lease fencing for recovery, automatic cache retention/cleanup and stable metadata cursor snapshots.
