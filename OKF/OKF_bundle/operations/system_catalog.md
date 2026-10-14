---
id: nc.operations.system_catalog
title: System Catalog
type: System
description: Authoritative system defining system catalog for NexaCore Operations
  operations.
tags:
- operations
- system
- catalog
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
- id: system_catalog-source
  resource: /Datasource/operations/system_catalog.json
  title: Source Document system_catalog.json
---

# System Catalog

## Catalog Metadata
- **Catalog Id**: NC-OPS-SYS-2026-08
- **Version**: 2.5
- **Effective Date**: 2026-08-01
- **Last Review**: 2026-07-31
- **Owner**: Operations Architecture
- **Classification**: Internal / Confidential
- **Description**: Synthetic system inventory for NexaCore RAG evaluation.


## Environment Definitions
- **Production**: Live customer or business workloads
- **Staging**: Production-like validation
- **Development**: Engineering development and testing
- **Recovery**: Secondary-region recovery capability


## Production Systems Inventory

| System ID | Name | Category | Criticality | Availability | RTO | RPO | Regions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **SYS-001** | NexaCore Identity Hub | Identity & Access | Tier-1 | 99.95% | 30m | 5m | IN-South-1 / IN-Central-1 |
| **SYS-002** | Customer Workspace | Customer Platform | Tier-1 | 99.9% | 60m | 15m | IN-South-1 / IN-Central-1 |
| **SYS-003** | Revenue CRM | Sales | Tier-2 | 99.5% | 240m | 60m | IN-South-1 / IN-Central-1 |
| **SYS-004** | ExpenseFlow | Finance | Tier-2 | 99.5% | 240m | 60m | IN-South-1 / IN-Central-1 |
| **SYS-005** | VendorHub | Procurement | Tier-2 | 99.5% | 240m | 60m | IN-South-1 / IN-Central-1 |
| **SYS-006** | ObjectVault | Storage | Tier-1 | 99.95% | 60m | 15m | IN-South-1 / IN-Central-1 |
| **SYS-007** | Analytics Lake | Data & Analytics | Tier-2 | 99.5% | 480m | 120m | IN-South-1 / IN-Central-1 |
| **SYS-008** | Support Desk | Customer Operations | Tier-2 | 99.5% | 240m | 60m | IN-South-1 / IN-Central-1 |
| **SYS-009** | API Gateway | Platform | Tier-1 | 99.95% | 30m | 5m | IN-South-1 / IN-Central-1 |
| **SYS-010** | EventBridge | Messaging | Tier-1 | 99.95% | 30m | 5m | IN-South-1 / IN-Central-1 |
| **SYS-011** | BuildForge CI | Developer Platform | Tier-3 | 99.0% | 720m | 240m | IN-South-1 / IN-Central-1 |
| **SYS-012** | PeopleCore | HR | Tier-2 | 99.5% | 240m | 60m | IN-South-1 / IN-Central-1 |
| **SYS-013** | Network Edge | Network | Tier-1 | 99.99% | 15m | 5m | IN-South-1 / IN-Central-1 |
| **SYS-014** | Secrets Vault | Security | Tier-1 | 99.99% | 15m | 5m | IN-South-1 / IN-Central-1 |
| **SYS-015** | Notification Service | Communications | Tier-2 | 99.5% | 240m | 60m | IN-South-1 / IN-Central-1 |
| **SYS-016** | Document Processing | Content | Tier-2 | 99.5% | 240m | 60m | IN-South-1 / IN-Central-1 |
| **SYS-017** | Security Monitor | Security Operations | Tier-1 | 99.95% | 30m | 5m | IN-South-1 / IN-Central-1 |
| **SYS-018** | ProcureLedger | Finance/Procurement | Tier-2 | 99.5% | 240m | 60m | IN-South-1 / IN-Central-1 |
| **SYS-019** | BillingCore | Finance | Tier-1 | 99.9% | 60m | 15m | IN-South-1 / IN-Central-1 |
| **SYS-020** | Data Catalog | Data Governance | Tier-3 | 99.0% | 720m | 240m | IN-South-1 / IN-Central-1 |


## Detailed System Specifications

### SYS-001: NexaCore Identity Hub
- **Category**: Identity & Access
- **Owner Team**: Security Engineering (Business Owner: Corporate IT)
- **Criticality Tier**: Tier-1 | Data Classification: Restricted
- **Availability Target**: 99.95% (RTO: 30m, RPO: 5m)
- **Authentication**: OIDC/SAML | Vendor: Internal Platform
- **Dependencies**: SYS-014, SYS-021


### SYS-002: Customer Workspace
- **Category**: Customer Platform
- **Owner Team**: Workspace Engineering (Business Owner: Product)
- **Criticality Tier**: Tier-1 | Data Classification: Confidential
- **Availability Target**: 99.9% (RTO: 60m, RPO: 15m)
- **Authentication**: OIDC | Vendor: Internal Platform
- **Dependencies**: SYS-001, SYS-006, SYS-009


### SYS-003: Revenue CRM
- **Category**: Sales
- **Owner Team**: Business Applications (Business Owner: Sales Operations)
- **Criticality Tier**: Tier-2 | Data Classification: Confidential
- **Availability Target**: 99.5% (RTO: 240m, RPO: 60m)
- **Authentication**: OIDC | Vendor: NexaCore Applications
- **Dependencies**: SYS-001, SYS-018


### SYS-004: ExpenseFlow
- **Category**: Finance
- **Owner Team**: Finance Systems (Business Owner: Finance Operations)
- **Criticality Tier**: Tier-2 | Data Classification: Confidential
- **Availability Target**: 99.5% (RTO: 240m, RPO: 60m)
- **Authentication**: OIDC | Vendor: NexaCore Applications
- **Dependencies**: SYS-001, SYS-019


### SYS-005: VendorHub
- **Category**: Procurement
- **Owner Team**: Operations Engineering (Business Owner: Procurement)
- **Criticality Tier**: Tier-2 | Data Classification: Confidential
- **Availability Target**: 99.5% (RTO: 240m, RPO: 60m)
- **Authentication**: OIDC | Vendor: NexaCore Applications
- **Dependencies**: SYS-001, SYS-018


### SYS-006: ObjectVault
- **Category**: Storage
- **Owner Team**: Platform Engineering (Business Owner: Data Platform)
- **Criticality Tier**: Tier-1 | Data Classification: Restricted
- **Availability Target**: 99.95% (RTO: 60m, RPO: 15m)
- **Authentication**: Workload Identity | Vendor: Managed Cloud
- **Dependencies**: SYS-014


### SYS-007: Analytics Lake
- **Category**: Data & Analytics
- **Owner Team**: Data Engineering (Business Owner: Data & AI)
- **Criticality Tier**: Tier-2 | Data Classification: Confidential
- **Availability Target**: 99.5% (RTO: 480m, RPO: 120m)
- **Authentication**: OIDC | Vendor: Managed Cloud
- **Dependencies**: SYS-006, SYS-014


### SYS-008: Support Desk
- **Category**: Customer Operations
- **Owner Team**: Business Applications (Business Owner: Customer Success)
- **Criticality Tier**: Tier-2 | Data Classification: Confidential
- **Availability Target**: 99.5% (RTO: 240m, RPO: 60m)
- **Authentication**: OIDC | Vendor: NexaCore Applications
- **Dependencies**: SYS-001


### SYS-009: API Gateway
- **Category**: Platform
- **Owner Team**: Platform Engineering (Business Owner: Engineering)
- **Criticality Tier**: Tier-1 | Data Classification: Internal
- **Availability Target**: 99.95% (RTO: 30m, RPO: 5m)
- **Authentication**: JWT/OIDC | Vendor: Internal Platform
- **Dependencies**: SYS-001, SYS-014


### SYS-010: EventBridge
- **Category**: Messaging
- **Owner Team**: Platform Engineering (Business Owner: Engineering)
- **Criticality Tier**: Tier-1 | Data Classification: Internal
- **Availability Target**: 99.95% (RTO: 30m, RPO: 5m)
- **Authentication**: Workload Identity | Vendor: Managed Cloud
- **Dependencies**: SYS-014


### SYS-011: BuildForge CI
- **Category**: Developer Platform
- **Owner Team**: Developer Experience (Business Owner: Engineering)
- **Criticality Tier**: Tier-3 | Data Classification: Internal
- **Availability Target**: 99.0% (RTO: 720m, RPO: 240m)
- **Authentication**: OIDC | Vendor: Internal Platform
- **Dependencies**: SYS-001, SYS-006


### SYS-012: PeopleCore
- **Category**: HR
- **Owner Team**: Business Applications (Business Owner: People Operations)
- **Criticality Tier**: Tier-2 | Data Classification: Restricted
- **Availability Target**: 99.5% (RTO: 240m, RPO: 60m)
- **Authentication**: OIDC | Vendor: NexaCore Applications
- **Dependencies**: SYS-001


### SYS-013: Network Edge
- **Category**: Network
- **Owner Team**: Infrastructure (Business Owner: IT)
- **Criticality Tier**: Tier-1 | Data Classification: Internal
- **Availability Target**: 99.99% (RTO: 15m, RPO: 5m)
- **Authentication**: Certificate/Identity | Vendor: Managed Network
- **Dependencies**: None


### SYS-014: Secrets Vault
- **Category**: Security
- **Owner Team**: Security Engineering (Business Owner: Security)
- **Criticality Tier**: Tier-1 | Data Classification: Restricted
- **Availability Target**: 99.99% (RTO: 15m, RPO: 5m)
- **Authentication**: Workload Identity/MFA | Vendor: Managed Security
- **Dependencies**: SYS-013


### SYS-015: Notification Service
- **Category**: Communications
- **Owner Team**: Platform Engineering (Business Owner: Product)
- **Criticality Tier**: Tier-2 | Data Classification: Internal
- **Availability Target**: 99.5% (RTO: 240m, RPO: 60m)
- **Authentication**: Workload Identity | Vendor: Internal Platform
- **Dependencies**: SYS-010


### SYS-016: Document Processing
- **Category**: Content
- **Owner Team**: AI Platform (Business Owner: Engineering)
- **Criticality Tier**: Tier-2 | Data Classification: Confidential
- **Availability Target**: 99.5% (RTO: 240m, RPO: 60m)
- **Authentication**: OIDC | Vendor: Internal Platform
- **Dependencies**: SYS-006, SYS-010


### SYS-017: Security Monitor
- **Category**: Security Operations
- **Owner Team**: Security Operations (Business Owner: Security)
- **Criticality Tier**: Tier-1 | Data Classification: Restricted
- **Availability Target**: 99.95% (RTO: 30m, RPO: 5m)
- **Authentication**: MFA | Vendor: Managed Security
- **Dependencies**: SYS-001, SYS-013, SYS-014


### SYS-018: ProcureLedger
- **Category**: Finance/Procurement
- **Owner Team**: Finance Systems (Business Owner: Procurement)
- **Criticality Tier**: Tier-2 | Data Classification: Confidential
- **Availability Target**: 99.5% (RTO: 240m, RPO: 60m)
- **Authentication**: OIDC | Vendor: NexaCore Applications
- **Dependencies**: SYS-001, SYS-006


### SYS-019: BillingCore
- **Category**: Finance
- **Owner Team**: Finance Systems (Business Owner: Finance)
- **Criticality Tier**: Tier-1 | Data Classification: Restricted
- **Availability Target**: 99.9% (RTO: 60m, RPO: 15m)
- **Authentication**: OIDC/MFA | Vendor: NexaCore Applications
- **Dependencies**: SYS-001, SYS-006, SYS-010


### SYS-020: Data Catalog
- **Category**: Data Governance
- **Owner Team**: Data Engineering (Business Owner: Data & AI)
- **Criticality Tier**: Tier-3 | Data Classification: Internal
- **Availability Target**: 99.0% (RTO: 720m, RPO: 240m)
- **Authentication**: OIDC | Vendor: Internal Platform
- **Dependencies**: SYS-001, SYS-007
