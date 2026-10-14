---
id: nc.operations.vendor_management
title: 1. Vendor Lifecycle
type: Specification
description: NexaCore Vendor Management Standard.
tags:
- operations
- specification
- vendor
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
- id: vendor_management-source
  resource: /Datasource/operations/vendor_management.docx
  title: Source Document vendor_management.docx
---

NexaCore Vendor Management Standard

Document ID: NC-OPS-VND-2026-08 | Version 4.0 | Effective 01 Aug 2026 | Owner: Procurement Operations

Synthetic private-company data created for RAG evaluation; not sourced from a real organization.


# 1. Vendor Lifecycle


Vendor management begins at supplier identification and continues through onboarding, contracting, performance monitoring, risk review, renewal and offboarding.




| Stage | Primary owner | Target |

| --- | --- | --- |

| Request | Business owner | 1 business day acknowledgement |

| Due diligence | Procurement + Risk | 5–15 business days |

| Contracting | Procurement + Legal | 5–20 business days |

| Onboarding | Procurement | 3 business days after approval |

| Performance review | Vendor owner | Monthly/quarterly |

| Offboarding | Vendor owner + IT/Finance | ≤10 business days |





## 1.1 Vendor record minimums


Vendor ID

Legal name

Service category

Risk tier

Contract dates

Business owner

Payment terms

Data access

System access

Insurance/compliance status

Renewal date


# 2. Due Diligence



## 2.1 Standard due-diligence package


Company registration and legal identity

Ownership information where required

Security questionnaire for applicable suppliers

Financial stability indicators for critical suppliers

Insurance certificates where required

Data-processing terms where applicable

Business continuity evidence

References for material strategic suppliers


## 2.2 Risk scoring





| Factor | Weight |

| --- | --- |

| Data sensitivity | 25% |

| Operational dependency | 20% |

| Security posture | 20% |

| Financial stability | 15% |

| Subcontractor exposure | 10% |

| Geographic/legal complexity | 10% |





## 2.3 Risk bands


Scores below 30 are Low, 30–59 Medium, 60–79 High and 80–100 Critical. A high or critical rating requires a documented mitigation plan before production dependency.


# 3. Contract and SLA Management



## 3.1 Contract controls


Executed agreement must be stored in the approved contract repository.

Material amendments require review of pricing, scope, security and service levels.

Auto-renewal dates should be tracked at least 90 days in advance.

Termination rights and notice periods must be recorded in the vendor record.


## 3.2 SLA measurement





| Service metric | Standard target | Escalation trigger |

| --- | --- | --- |

| Availability | ≥99.9% for critical service | Below target in month |

| Support response | ≤60 min critical | Missed critical SLA |

| Resolution | ≤4 hr critical | Repeated breach |

| Delivery | ≥95% on time | <90% for 2 months |

| Invoice accuracy | ≥98% | <95% |





## 3.3 Service credits


Contractual service credits are tracked by Procurement and Finance. Acceptance of a service credit does not automatically waive other contractual remedies.


# 4. Vendor Performance Reviews



## 4.1 Monthly scorecard





| Dimension | Weight |

| --- | --- |

| Service quality | 25% |

| SLA performance | 20% |

| Delivery reliability | 20% |

| Commercial value | 15% |

| Security/compliance | 15% |

| Relationship management | 5% |





## 4.2 Score interpretation


Scores ≥90 are Preferred, 80–89 Healthy, 70–79 Watch and <70 Corrective Action Required.


## 4.3 Corrective action


Document issue and evidence.

Agree corrective action and due date.

Assign supplier and internal owners.

Track weekly for critical issues.

Escalate unresolved high-risk issues to Procurement Head.

Consider alternate supplier if remediation fails.


# 5. Renewal and Offboarding



## 5.1 Renewal timeline


120 days before expiry: confirm business need and spend.

90 days: performance and risk review.

60 days: commercial negotiation / alternatives.

30 days: final approval and contract execution.

Post-renewal: update vendor record and repository.


## 5.2 Offboarding checklist


Revoke system access.

Recover company assets where applicable.

Confirm data return/deletion obligations.

Stop purchase orders.

Close open invoices.

Archive contract and performance record.

Document termination reason.


## 5.3 Exit risk


Critical vendors require a documented exit plan covering replacement options, data portability, transition period, key dependencies and estimated switching cost.


# 6. FY26 Vendor Portfolio





| Metric | FY26 value |

| --- | --- |

| Active vendors | 612 |

| Critical vendors | 18 |

| High-risk vendors | 29 |

| Vendors reviewed during year | 487 |

| Vendors with corrective actions | 54 |

| Average vendor score | 84.7 |

| Contracts renewed | 391 |

| Contracts terminated | 37 |

| Vendor-related incidents | 11 |

| Critical vendor exit plans tested | 14 |





## 6.1 Ownership rules


Every active vendor must have an internal business owner. Vendors without an owner are placed on the remediation queue and may be suspended from new commitments.


## Document control


NC-OPS-VND-2026-08 | Version 4.0 | Next review 31 Jul 2027.
