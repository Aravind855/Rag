---
id: nc.operations.business_continuity
title: Business Continuity
type: Specification
description: Authoritative specification defining business continuity for NexaCore
  Operations operations.
tags:
- operations
- specification
status: stable
stale_after: '2027-08-01T00:00:00Z'
version: '1.0'
owners:
- operations-operations@nexacore.internal
generated:
  by: automated-okf-parser-pipeline
  at: '2026-10-14T00:00:00Z'
verified:
  by: Head of Operations Governance
  at: '2026-10-14T00:00:00Z'
sources:
- id: business_continuity-source
  resource: /Datasource/operations/business_continuity.pptx
  title: Source Document business_continuity.pptx
---

# Business Continuity

## Slide 1: NexaCore Business Continuity Overview

- Version 2.3 | Effective 01 August 2026 | Operations & Risk


## Slide 2: Continuity Objectives

- Protect people first, then preserve critical customer and business services.
- Maintain defined recovery targets for Tier-1 and Tier-2 capabilities.
- Reduce dependency on single facilities, suppliers and technical components.
- Use documented recovery procedures and exercise them regularly.
- Communicate confirmed impact and recovery expectations through incident management.
- NexaCore Business Continuity | Internal


## Slide 3: Continuity Architecture

- Primary Region
- Secondary Recovery
- People / Operations
- Critical Suppliers


## Slide 4: Criticality and Recovery Targets

- Tier-1 services: RTO 60 minutes, RPO 15 minutes.
- Tier-2 services: RTO 4 hours, RPO 1 hour.
- Internal low-criticality tools: best-effort recovery unless service-specific target exists.
- Recovery targets are validated against architecture, backup capability and supplier dependencies.
- NexaCore Business Continuity | Internal


## Slide 5: Business Impact Priorities

- Priority 1: customer-facing services, security controls and revenue-critical transaction paths.
- Priority 2: workforce identity, communications, finance operations and key internal workflows.
- Priority 3: non-critical analytics, development tools and convenience services.
- Business owners review criticality at least annually or after major service changes.
- NexaCore Business Continuity | Internal


## Slide 6: People and Workplace Continuity

- Critical functions maintain named primary and secondary owners.
- Remote-work capability is included in continuity planning for suitable roles.
- Emergency contact trees are reviewed quarterly.
- Critical teams maintain minimum staffing plans for 24-hour disruption scenarios.
- Site disruption plans identify alternate work locations or remote operating procedures.
- NexaCore Business Continuity | Internal


## Slide 7: Technology Recovery

- Backups for Tier-1 systems follow service-specific RPO requirements.
- Restore procedures are tested quarterly for selected Tier-1 workloads.
- Recovery environments are access-controlled and monitored.
- Critical dependencies are documented in the system catalog.
- Post-recovery validation includes data integrity, authentication, monitoring and customer transaction checks.
- NexaCore Business Continuity | Internal


## Slide 8: Supplier Continuity

- Critical suppliers require continuity evidence and an exit/alternative plan.
- Single-source dependencies are tracked as continuity risks.
- Supplier critical incidents are escalated through the vendor management process.
- Material supplier changes require business-owner review before acceptance.
- NexaCore Business Continuity | Internal


## Slide 9: Exercise Program

- Quarterly tabletop exercise: one critical business scenario.
- Semiannual technical recovery test: selected system restore/failover.
- Annual enterprise continuity exercise: cross-functional scenario.
- Exercise findings receive owners and target dates.
- FY26: 17 continuity exercises completed; 94% of corrective actions closed within target.
- NexaCore Business Continuity | Internal


## Slide 10: Scenario Playbooks

- Cloud region disruption: assess health, declare continuity mode, shift eligible workloads and validate critical paths.
- Identity-provider outage: activate approved emergency access process and prioritize critical operational users.
- Office/site outage: move affected teams to remote/alternate operating model.
- Critical supplier failure: activate alternate supplier or manual workaround and notify business owner.
- Cyber incident: follow Security Incident Response Runbook before restoration.
- NexaCore Business Continuity | Internal


## Slide 11: FY26 Continuity Metrics

- Tier-1 services with documented recovery plans: 100%.
- Tier-1 restore tests completed: 96%.
- Critical business functions with alternate owner: 98.2%.
- Critical supplier exit plans tested: 14.
- Average Tier-1 recovery exercise duration: 47 minutes.
- Open high-priority continuity actions at 31 July 2026: 3.
- NexaCore Business Continuity | Internal


## Slide 12: Governance and Document Control

- Owner: Operations & Risk.
- Version: 2.3.
- Effective: 01 August 2026.
- Next review: 31 July 2027.
- Continuity plans are reviewed after major incidents, material architecture changes and significant supplier changes.
- Classification: Internal / Confidential.
- NexaCore Business Continuity | Internal
