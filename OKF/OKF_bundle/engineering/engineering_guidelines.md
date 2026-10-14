---
id: nc.engineering.engineering_guidelines
title: 1. Engineering Operating Principles
type: Standard
description: NexaCore Engineering Guidelines.
tags:
- engineering
- standard
status: stable
stale_after: '2027-08-01T00:00:00Z'
version: '1.0'
owners:
- engineering-operations@nexacore.internal
generated:
  by: automated-okf-parser-pipeline
  at: '2026-10-14T00:00:00Z'
verified:
  by: Head of Engineering Governance
  at: '2026-10-14T00:00:00Z'
sources:
- id: engineering_guidelines-source
  resource: /Datasource/engineering/engineering_guidelines.docx
  title: Source Document engineering_guidelines.docx
---

NexaCore Engineering Guidelines

Document ID: NC-ENG-GDL-2026-08 | Version 4.2 | Effective 01 Aug 2026 | Owner: Platform Engineering

Synthetic private company data created for RAG evaluation. It is not copied from a real organization.


# 1. Engineering Operating Principles


Engineering teams are expected to optimize for correctness, maintainability, security and operational reliability rather than short-term code volume. Every production change must have an identifiable owner and an auditable path from requirement to deployment.


## 1.1 Quality priorities





| Priority | Expected behavior | Measurement |

| --- | --- | --- |

| Correctness | Tests cover business-critical paths | Critical path test coverage ≥ 85% |

| Reliability | Services expose health/readiness signals | SLO defined for production services |

| Security | Secrets and privileged operations use approved controls | Zero hard-coded production secrets |

| Maintainability | Code follows repository conventions | Review checklist + static analysis |

| Observability | Failures produce actionable telemetry | Logs + metrics + traces where applicable |





## 1.2 Repository standards


Every production repository must have an owner, README, license/notice file where required, dependency manifest and CI configuration.

Default branches are protected; direct pushes to protected production branches are prohibited.

Commit messages should identify the intent of a change. Squashed merge commits should reference the ticket or change request.

Repository secrets must never be committed, including local development credentials copied into configuration files.

Generated artifacts should be separated from source code and must not be committed unless the repository explicitly requires them.


## 1.3 Definition of done


A change is considered complete only when implementation, tests, review, documentation, monitoring impact and deployment notes are addressed. For customer-impacting changes, rollback or mitigation steps must be documented before production approval.


# 2. Code Review and Branching



## 2.1 Branch naming





| Type | Pattern | Example |

| --- | --- | --- |

| Feature | feature/<ticket>-<short-name> | feature/ENG-1842-rate-limit |

| Bug fix | fix/<ticket>-<short-name> | fix/ENG-1910-null-cache |

| Hotfix | hotfix/<incident>-<short-name> | hotfix/INC-773-auth-timeout |

| Chore | chore/<ticket>-<short-name> | chore/ENG-1820-upgrade-sdk |





## 2.2 Review requirements


Normal production changes require at least 1 qualified reviewer.

Changes to authentication, authorization, secrets, payment logic or data-retention controls require 2 reviewers, including a domain owner where assigned.

Database migrations that can lock or rewrite large tables require an explicit migration plan and rollback/forward-fix strategy.

A reviewer should reject a change when requirements are unclear, tests are insufficient, security impact is unexplained, or operational ownership is missing.

Large pull requests above 800 changed lines should normally be split unless the change is generated, mechanical or migration-driven.


## 2.3 Review turnaround targets





| PR class | Target first review | Escalation |

| --- | --- | --- |

| Routine | Within 1 business day | Team lead after 2 days |

| High priority | Within 4 working hours | Engineering manager after 8 hours |

| Hotfix | Within 30 minutes | On-call lead |

| Security remediation | Within 2 working hours | Security engineering |





## 2.4 Testing expectations


Unit tests should validate deterministic business logic. Integration tests should cover service boundaries and persistence behavior. End-to-end tests should be reserved for critical user journeys because they carry higher runtime and maintenance cost.


# 3. API, Data and Dependency Practices



## 3.1 API implementation


API contracts must define authentication, request validation, response schema and error behavior.

Breaking changes require versioning or an approved compatibility migration.

Endpoints should reject unknown or invalid input rather than silently coercing unsafe values.

Pagination is required for collections that can exceed 100 records under expected production volume.

Request IDs must be propagated across service calls when supported by the platform.


## 3.2 Database changes





| Change type | Required control | Default deployment pattern |

| --- | --- | --- |

| Add nullable column | Schema review | Expand → deploy → backfill |

| Add index | Query impact review | Online/low-lock method where supported |

| Rename column | Compatibility plan | Dual-read/write → migrate → remove |

| Delete column | Usage evidence | Deprecate → verify → remove |

| Large backfill | Capacity estimate | Throttled batches + monitoring |





## 3.3 Dependency management


Dependencies must use approved registries and lock files where the ecosystem supports them.

Critical vulnerabilities must be triaged within 24 hours of confirmed production exposure.

Major dependency upgrades require compatibility testing and release notes review.

Unused dependencies should be removed during quarterly repository hygiene reviews.


## 3.4 Configuration


Configuration should be externalized by environment. Local defaults must not accidentally point to production services. Production configuration changes should be auditable and should not require source-code modification unless the platform design explicitly requires it.


# 4. Observability, Performance and Reliability



## 4.1 Standard telemetry





| Signal | Minimum requirement | Retention target |

| --- | --- | --- |

| Application logs | Structured JSON + request/correlation ID | 30 days |

| Metrics | Latency, errors, throughput, saturation | 90 days |

| Traces | Critical distributed paths | 14 days |

| Audit events | Security-sensitive actions | 365 days |





## 4.2 Performance budgets


Interactive API endpoints should target p95 latency below 500 ms for normal reads and below 800 ms for normal writes unless the contract specifies otherwise.

Background jobs must expose queue age and processing duration.

Services should define a resource saturation threshold before production launch; 80% sustained CPU or memory is a common review trigger, not a universal limit.

Performance regressions above 20% on a critical endpoint require investigation before release unless the change is explicitly accepted.


## 4.3 Reliability targets


Production services must document an SLO appropriate to business criticality. The current platform reference uses 99.9% monthly availability for Tier-1 APIs, 99.5% for Tier-2 services and best-effort targets for internal development tools.


## 4.4 Incident learning


Incidents affecting customers or production data require a written post-incident review.

The review should identify timeline, impact, detection, contributing factors, corrective actions and owners.

Corrective actions should have target dates; recurring incidents are reviewed during the monthly reliability meeting.


# 5. Security and Secure Development



## 5.1 Secure coding controls


Validate input at the application boundary and enforce authorization at the resource boundary.

Do not log passwords, access tokens, session cookies, API keys or full payment-card information.

Use parameterized queries or approved ORM mechanisms instead of string-built SQL.

Cryptographic operations must use approved platform libraries; custom cryptography is prohibited.

Production secrets must be stored in the approved secret-management system.


## 5.2 Security severity targets





| Severity | Initial response | Target remediation |

| --- | --- | --- |

| Critical | ≤ 1 hour | ≤ 24 hours |

| High | ≤ 4 hours | ≤ 7 calendar days |

| Medium | ≤ 2 business days | ≤ 30 calendar days |

| Low | ≤ 5 business days | ≤ 90 calendar days |





## 5.3 Access control


Engineering access follows least privilege. Production access is role-based, time-bounded where supported and logged. Developers should use non-production environments for debugging unless an approved production diagnostic procedure exists.


## 5.4 Release gates


CI must pass before merge.

Required security scans must pass or have an approved exception.

Database migrations must complete successfully in the deployment sequence.

Smoke tests must pass after production rollout.


# 6. Engineering Metrics and Governance



## 6.1 FY26 engineering snapshot





| Metric | FY26 value | Reference interpretation |

| --- | --- | --- |

| Production services | 42 | Services with active production ownership |

| Tier-1 services | 11 | Customer/revenue/security critical |

| Average deployment frequency | 8.7 / week | Across production services |

| Change failure rate | 7.4% | Deployments requiring rollback/hotfix |

| Median lead time | 19.6 hours | Commit/merge to production |

| Critical vulnerabilities overdue | 1 | At 31 Jul 2026 |

| Repositories with CODEOWNERS | 93% | Engineering repositories |

| Automated test suites | 187 | CI-managed suites |





## 6.2 Governance cadence


Weekly engineering operations review: deployment health, incidents, change failures and capacity.

Monthly architecture review: major design changes, service boundaries and technical debt.

Quarterly dependency review: vulnerable packages, obsolete libraries and upgrade roadmap.

Semiannual repository ownership review: owners, escalation paths and business criticality.


## 6.3 Exception management


Engineering exceptions must include the affected system, requirement being waived, risk, compensating control, owner and expiry date. Permanent exceptions require an architecture or security decision record.

Document control: NC-ENG-GDL-2026-08 | Version 4.2 | Next review 31 Jul 2027.
