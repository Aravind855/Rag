# NexaCore API Engineering Standards

**Document ID:** NC-ENG-API-2026-08  
**Version:** 5.0  
**Effective:** 01 Aug 2026  
**Owner:** Platform Engineering  
**Status:** Internal / Controlled  
**Data classification:** Internal

> This document is synthetic private company data created for RAG evaluation. It is not sourced from a real company.

## 1. API Design Baseline

NexaCore APIs use HTTP semantics consistently and expose machine-readable contracts.

### 1.1 Standard resource conventions

| Item | Standard |
|---|---|
| Base path | `/api/v1` |
| JSON media type | `application/json` |
| Authentication | OAuth2/JWT depending on service |
| Request ID | `X-Request-ID` |
| Trace ID | `X-Trace-ID` |
| Maximum page size | 100 |
| Default page size | 25 |
| Maximum request body | 2 MB unless service exception |
| Default timeout | 30 seconds |
| Maximum synchronous timeout | 60 seconds |

Resource names are plural nouns: `/users`, `/projects`, `/invoices`.

Avoid verbs in resource paths except for explicitly modeled actions such as `/password-reset` or `/token`.

## 2. HTTP Status Standards

| Situation | Status |
|---|---:|
| Successful read | 200 |
| Resource created | 201 |
| Accepted asynchronous operation | 202 |
| Successful delete with no body | 204 |
| Invalid request syntax/validation | 400 |
| Missing/invalid authentication | 401 |
| Authenticated but not authorized | 403 |
| Resource not found | 404 |
| Conflict / duplicate state | 409 |
| Rate limit exceeded | 429 |
| Unexpected server failure | 500 |
| Temporary upstream dependency failure | 503 |

A successful API must not return `200` for a failed business operation merely because the HTTP request reached the server.

## 3. Error Contract

All APIs should use a predictable error structure:

```json
{
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "The requested project does not exist.",
    "request_id": "req_7f31...",
    "details": []
  }
}
```

### 3.1 Error-code rules

- Codes are uppercase `SCREAMING_SNAKE_CASE`.
- Codes are stable identifiers; clients should not parse the human message.
- Do not expose database exception messages.
- Validation errors should identify the field where possible.
- Security-sensitive errors should not reveal whether a protected resource exists.

## 4. Pagination

Collection endpoints must paginate when expected result volume can exceed 100 records.

Preferred response:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total": 413,
    "has_next": true
  }
}
```

For high-volume or distributed data, cursor pagination may be used:

```json
{
  "data": [],
  "next_cursor": "eyJvZmZzZXQiOjI1fQ=="
}
```

Cursor values must be opaque to clients.

## 5. Filtering, Sorting and Search

Supported query parameters should be explicitly documented.

Example:

`GET /api/v1/orders?status=OPEN&sort=-created_at&page_size=25`

Rules:

1. Do not expose arbitrary database field expressions.
2. Allow-list sortable fields.
3. Validate enum values.
4. Normalize date/time inputs to ISO 8601.
5. Define whether filtering is case-sensitive.
6. Search endpoints should define maximum query length.

## 6. Idempotency

POST requests that create financial, provisioning or other non-repeatable side effects should support an idempotency key.

Header:

`Idempotency-Key: 7d9d7e1e-...`

The server should return the original result for a repeated key where the request body is equivalent.

Recommended retention for payment/provisioning operations: **24 hours minimum**.

## 7. Authentication and Authorization

Authentication proves identity; authorization determines access.

Required controls:

- Validate token issuer, audience, expiry and signature.
- Enforce authorization at the service/resource boundary.
- Never trust a user-provided `user_id` merely because it appears in the URL.
- Administrative endpoints require explicit role/permission checks.
- Service-to-service credentials must use managed identity or approved secret storage.

## 8. Rate Limiting

Default platform limits:

| Consumer type | Sustained rate | Burst |
|---|---:|---:|
| Standard user | 60 req/min | 20 |
| Service client | 300 req/min | 100 |
| Internal batch client | 600 req/min | 200 |
| Authentication endpoints | 10 req/min/IP | 5 |

Rate-limit responses use HTTP `429` and should include `Retry-After` when practical.

## 9. Versioning and Compatibility

The public API major version is represented in the path, e.g. `/api/v1`.

Breaking changes include:

- Removing a field.
- Changing a field's type.
- Making an optional field mandatory.
- Changing semantic meaning.
- Removing an endpoint.

Non-breaking additions should remain backward compatible.

A deprecated endpoint should normally receive at least **90 days** of notice before removal unless security or legal requirements require faster action.

## 10. Time and Date Rules

- Store timestamps in UTC.
- APIs should return ISO 8601 timestamps with timezone information.
- Business-local dates must be represented as dates rather than midnight UTC timestamps.
- Never infer a user's timezone from browser locale alone when financial or scheduling correctness matters.

## 11. API Performance Targets

| API class | Target |
|---|---:|
| Simple read | p95 < 300 ms |
| Normal read/write | p95 < 500 ms |
| Complex query | p95 < 800 ms |
| Synchronous external workflow | p95 < 2 s |
| Absolute synchronous timeout | 60 s |

A sustained p95 regression greater than 20% requires investigation.

## 12. Documentation Requirements

Every production API must document:

- Purpose and ownership
- Authentication
- Endpoint list
- Request/response schemas
- Error codes
- Rate limits
- Pagination
- Examples
- Deprecation status
- Operational dependencies

**Review cadence:** quarterly.  
**Current owner:** Platform Architecture Council.
