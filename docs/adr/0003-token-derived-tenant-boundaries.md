# ADR 0003: Derive tenant boundaries from verified identity

## Status

Accepted.

## Context

The initial scaffold accepted `X-Organization-ID` so tenant-scoped database queries could be developed and tested before authentication. A caller can freely modify that header, so it cannot protect customer records or future private images.

## Decision

- Authenticate API requests with signed Bearer tokens.
- Read user, organization, email, and role from verified claims.
- Revalidate the subject, organization, email, active status, and current role against PostgreSQL on every request.
- Derive every organization-owned database query from the authenticated principal.
- Provide an HS256 development issuer only when `AUTH_MODE=development`.
- Validate production OIDC/Cognito tokens through RS256 and the configured JWKS endpoint.
- Enforce permissions through explicit role dependencies.

## Consequences

- Changing or reintroducing an organization header cannot switch tenant scope.
- Disabled users and stale role tokens are rejected immediately.
- Local development remains simple without pretending that development token issuance is production login.
- Cognito configuration can replace the local issuer without rewriting route authorization.
- Customer self-service ownership policies still need to be added with the customer portal identity model.

