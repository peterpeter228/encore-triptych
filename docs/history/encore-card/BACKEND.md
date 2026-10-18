# 安可三联 · local backend

## Run

Python 3.12, FastAPI, Uvicorn and Pillow are required. From this directory:

    python app.py

Open http://127.0.0.1:8765. `PORT` changes the port; `ENCORE_DATA_DIR` changes the private data directory. The default is `./data`. This is a local-only demo, not deployed and not reachable by a friend's device. Running the frontend without the Python backend will not persist contributions.

The API serves `/api/health`; the static frontend is served both at `/` and `/static/`. No CDN, tracking, wallet, email or paid service is used. Access logging is disabled because invite paths contain access capabilities. Do not enable access logging or publicly proxy this prototype without a security/deployment review. Run one Uvicorn process only. The application rejects non-local Host and cross-origin requests.

## Capabilities and privacy

- Owner, read-only viewer, invitation and individual contribution keys are distinct. Keep management links/keys private. There is no password reset or account recovery.
- Browser-facing shared URLs should keep keys in URL fragments. API calls send `Authorization: Bearer KEY`. Invite lookup/join uses an unguessable token in the API path.
- Only creation returns the owner key. Public event responses contain no keys. Contributors receive their own edit key and a read-only view key, never the owner's.
- An owner may change/withdraw only their own contribution, rotate/revoke invitations or delete the entire event. Other contributors may change/withdraw only their own contribution. Read-only access cannot write.
- Revoking an invitation stops new joins, not existing readers/contributors. Already downloaded screenshots/exports cannot be revoked. There is no public listing.
- These are bearer capabilities, not verified human identities. Capacity is three slots, not three identity-verified people. Sharing a management key shares that authority. Request UUIDs are retry credentials and must also remain private.
- SQLite holds content and hashes of access keys. A server-side secret derives creation/retry credentials. Anyone with filesystem access to the database should be treated as having full access.
- Uploaded images remain local. The server decodes only JPEG/PNG/WebP, verifies <=8 MiB and <=20 million pixels, applies EXIF rotation, resizes to <=1800×1800 and re-encodes JPEG without metadata. It never serves supplied filenames, SVG, HTML or raw uploads. Images require authenticated fetches, not public media URLs.
- Withdraw deletes that contribution and its stored image. Event deletion removes all content/media and leaves only a one-way retry-request tombstone to prevent accidental resurrection. This is logical deletion, not forensic disk erasure. Local external backups and downloaded copies are outside the app's control.

## API

JSON create: `POST /api/events` with `title` (1–80), ISO `date`, `organizer` (1–40), `nickname` (1–40), `caption` (0–280), `demo` (`stage`, `crowd`, `lights`, or null), and `request_id` (16–100 chars; browser should use crypto.randomUUID()). Returns `event`, `owner_key`, `view_key`, `invite_token`, `contribution_key`, `contribution_id`.

Event: `{id,title,date,organizer,created_at,count,contributions:[{id,slot,nickname,caption,demo,image_url}]}`. Slots are 0–2. Text is returned as JSON and must be rendered as text by the frontend, never HTML.

- `GET /api/events/ID`: read with any current valid event capability.
- `GET /api/invites/TOKEN`: read with a valid invitation.
- `POST /api/invites/TOKEN/join`: JSON nickname/caption/demo/request_id; returns event/view_key/contribution_key/contribution_id.
- `PUT /api/events/ID/contributions/CID`: JSON nickname/caption/demo; own edit or original-owner key.
- `PUT /api/events/ID/contributions/CID/image`: raw file bytes, not multipart; own key. Returns updated event.
- `GET /api/events/ID/contributions/CID/image`: authenticated image fetch, then browser blob URL.
- `DELETE /api/events/ID/contributions/CID`: withdraw own contribution; 204.
- `POST /api/events/ID/invite`: owner rotates invitation; returns invite_token.
- `DELETE /api/events/ID/invite`: owner revokes; 204.
- `DELETE /api/events/ID`: owner deletes entire event; 204.

Keep the same request_id for transport retries of the same create/join. A new user action needs a fresh UUID. Retry uses the original stored content, not changed retry fields. Create retry returns invite_token null if its original invite was rotated/revoked. Join retry after withdrawal and create retry after event deletion return 410. Maximum capacity conflicts return 409; invalid/revoked invites 404; invalid payloads 422; uploads above 8 MiB 413; malformed/unacceptable image 400. Unauthorized keys return 401/403. Deleting already removed contributions/events is a no-op.

SQLite `BEGIN IMMEDIATE`, unique slot constraints and per-process mutation locks make capacity checks/write atomic. A file is written with a random internal name, its DB reference is committed, then an old file is removed. Startup removes unreferenced JPEGs left by process interruption. A failed replacement upload does not erase an existing image. Run one process: startup orphan cleanup is not intended for multiple independently starting workers.

## Test

    python -m pytest tests/test_backend.py -q

Tests use isolated temporary directories and synthetic images. They cover capability separation, retry deduplication, concurrent joins, slot cap, revoke/rotate, contribution withdrawal, media protection and metadata stripping, malformed/oversized media, restart persistence, path isolation, deletion cleanup and crash-orphan cleanup.

Limitations before any public launch: no accounts or identity verification, invitation abuse/rate limits, operational quotas, backup policy, moderation/reporting, distributed storage, multiworker guarantees, recovery flows or external collaborative hosting. Three local browser sessions simulate collaboration; they do not establish demand or real sharing conversion.
