# ADR 0001: Establish application boundaries before adding an LLM

## Status

Accepted.

## Context

An LLM can propose answers and work orders, but it cannot be trusted to enforce organization isolation, authorization, validation, or approval. Starting with a chatbot would hide these missing controls and encourage AI-generated state changes.

## Decision

Build organization-scoped properties and human-managed work orders before document retrieval or model integration. Treat the model as an untrusted proposal generator. Application code owns identity, authorization, validation, persistence, and approval.

## Consequences

- The first milestone is less visually impressive but establishes credible production boundaries.
- Future retrieval must always include organization and property filters.
- Future AI tools will return typed proposals rather than writing directly to the database.
- Human approval will remain mandatory for operational state changes.

