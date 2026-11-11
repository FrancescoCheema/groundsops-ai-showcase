# ADR 0004: Store sanitized site captures behind tenant authorization

## Status

Accepted.

## Decision

GroundsOps decodes and re-encodes every accepted JPEG, PNG or WebP upload before
storage. This removes EXIF/GPS metadata and rejects files that merely claim to
be images. Stored objects use opaque tenant/design/capture keys and are returned
only through authenticated, tenant-scoped API endpoints.

The application depends on an object-storage interface. Local development uses
private filesystem storage; production will implement the same interface with
a private S3 bucket and short-lived access or API streaming.

## Consequences

- The original bytes are intentionally not retained.
- Re-encoding can change file size and JPEG pixels slightly.
- Database rows provide lifecycle, ownership, integrity hash and audit metadata.
- Soft-deleted metadata remains available for future audit policy while object
  bytes are removed immediately.
