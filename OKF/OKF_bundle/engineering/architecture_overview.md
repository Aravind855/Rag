---
id: nc.engineering.architecture_overview
title: Architecture Overview
type: Specification
description: Authoritative specification defining architecture overview for NexaCore
  Engineering operations.
tags:
- engineering
- specification
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
- id: architecture_overview-source
  resource: /Datasource/engineering/architecture_overview.pptx
  title: Source Document architecture_overview.pptx
---

# Architecture Overview

## Slide 1: NexaCore Engineering Architecture Overview

- Platform topology, service boundaries, data flows and reliability model
- Version 2.6 | August 2026


## Slide 2: Architecture at a Glance

- Web and mobile clients → API Gateway → domain services → data and integration layers.
- 42 production services are grouped into Tier-1, Tier-2 and internal utility classifications.
- Primary synchronous transport: HTTPS/REST; asynchronous workloads use the event bus.
- Observability is centralized across logs, metrics, traces and audit events.
- Production runs across two availability zones in the primary region with a secondary recovery region.
- NexaCore Architecture | Internal


## Slide 3: Logical Service Topology

- Clients
- API Gateway
- Domain Services
- Data Layer
- Event Bus
- External Systems
- Gateway responsibilities: authentication handoff, request correlation, rate limiting and routing. Domain services own business rules; the data layer owns persistence boundaries.


## Slide 4: Service Classification

- Tier-1: 11 services supporting customer, revenue or security-critical workflows.
- Tier-2: 23 services supporting important internal or customer-adjacent capabilities.
- Utility/internal: 8 services with lower business criticality and best-effort availability.
- Each production service must have an owner, repository, runbook, SLO and escalation path.
- Service ownership is reviewed quarterly; orphaned services are not permitted to remain in production.
- NexaCore Architecture | Internal


## Slide 5: Data Architecture

- Transactional workloads use relational storage where consistency and referential integrity are primary requirements.
- Document-oriented storage is used for flexible metadata and selected workflow records.
- Object storage contains large immutable artifacts; database rows retain metadata and references.
- Analytics workloads consume curated datasets rather than directly querying operational databases.
- Sensitive data is classified and access-controlled at the application and storage layers.
- NexaCore Architecture | Internal


## Slide 6: Event-Driven Processing

- Asynchronous workflows use domain events to decouple producers from consumers.
- Events contain event_id, event_type, occurred_at, producer, schema_version and payload.
- Consumers must be idempotent because delivery may be retried.
- Dead-letter queues are monitored and reviewed at least daily for Tier-1 event streams.
- Schema changes must preserve consumer compatibility or use a new event version.
- NexaCore Architecture | Internal


## Slide 7: API and Integration Layer

- External integrations terminate through approved integration services rather than allowing arbitrary outbound calls from domain services.
- Outbound calls use timeouts, retry policies and circuit-breaking where appropriate.
- Default retry policy: maximum 3 attempts with exponential backoff for retry-safe operations.
- Authentication secrets are stored in managed secret storage; credentials are never embedded in code.
- Partner integrations must document rate limits, failure behavior and support ownership.
- NexaCore Architecture | Internal


## Slide 8: Availability and Resilience

- Tier-1 reference target: 99.9% monthly availability.
- Tier-1 recovery target: RTO 60 minutes; RPO 15 minutes.
- Production workloads use zone-aware deployment for supported services.
- Critical dependencies must have documented degradation behavior.
- Quarterly recovery exercises validate selected backup, restore and failover paths.
- NexaCore Architecture | Internal


## Slide 9: Observability Architecture

- Structured logs include timestamp, service, environment, severity and correlation/request ID.
- Metrics cover traffic, errors, latency and saturation.
- Distributed traces connect gateway requests to downstream service calls where instrumentation is available.
- Audit events are retained separately from application debug logs.
- Alerting is tied to customer impact and SLO risk rather than every low-level exception.
- NexaCore Architecture | Internal


## Slide 10: Security Boundaries

- Identity is centralized; services validate authorization for their owned resources.
- Production administrative access is privileged, logged and reviewed.
- Network segmentation separates public ingress, application workloads, data services and management paths.
- Secrets are retrieved at runtime from approved secret-management infrastructure.
- Restricted data must not be copied into development environments without approved masking or synthetic replacement.
- NexaCore Architecture | Internal


## Slide 11: Deployment Architecture

- CI produces a versioned artifact tied to a source commit.
- Staging is the final production-like validation environment.
- Production rollout uses controlled promotion, with canary or phased deployment for Tier-1 services where supported.
- Rollback is preferred when the previous artifact is safe and compatible; irreversible migrations require forward-fix planning.
- Post-deployment smoke tests verify critical paths before the release is considered complete.
- NexaCore Architecture | Internal


## Slide 12: Architecture Decision Rules

- Prefer boring, observable technology over novelty when business requirements are equivalent.
- A new service requires a clear ownership boundary and justification for operational overhead.
- Shared databases between independent services require architecture review.
- New asynchronous messaging must define ordering, retry, idempotency and dead-letter behavior.
- Technology decisions with material security, cost or availability impact require an Architecture Decision Record.
- NexaCore Architecture | Internal


## Slide 13: FY26 Architecture Health Snapshot

- 42 production services; 11 Tier-1.
- 93% of engineering repositories have CODEOWNERS.
- 82% of Tier-1 services use canary rollout.
- 91% automated smoke-test coverage across production release paths.
- 7.4% FY26 change failure rate; target for FY27 is below 6%.
- 1 critical vulnerability was overdue as of 31 July 2026 and had an active remediation owner.
- NexaCore Architecture | Internal


## Slide 14: Document Control

- Document ID: NC-ENG-ARCH-2026-08
- Version: 2.6
- Effective: 01 August 2026
- Owner: Platform Architecture Council
- Next review: 31 July 2027
- Classification: Internal / Confidential
- NexaCore Architecture | Internal
