---
id: nc.finance.reimbursement_policy
title: 1. Reimbursement Lifecycle
type: Policy
description: NexaCore Reimbursement Procedure.
tags:
- finance
- policy
status: stable
stale_after: '2027-08-01T00:00:00Z'
version: '1.0'
owners:
- finance-operations@nexacore.internal
generated:
  by: automated-okf-parser-pipeline
  at: '2026-10-14T00:00:00Z'
verified:
  by: Head of Finance Governance
  at: '2026-10-14T00:00:00Z'
sources:
- id: reimbursement_policy-source
  resource: /Datasource/finance/reimbursement_policy.docx
  title: Source Document reimbursement_policy.docx
---

NexaCore Reimbursement Procedure

Document ID: NC-FIN-REIM-2026-08 | Version 3.4 | Effective 01 Aug 2026 | Owner: Finance Operations

Synthetic private-company document created for RAG evaluation; not sourced from a real company.


# 1. Reimbursement Lifecycle


The reimbursement process moves through five states: Draft → Submitted → Manager Approved → Finance Reviewed → Paid. A claim can be returned to Draft for correction when required evidence is missing.


## 1.1 Standard timeline





| Step | Target | Owner |

| --- | --- | --- |

| Employee submission | ≤ 30 calendar days | Employee |

| Manager review | ≤ 3 business days | Manager |

| Finance review | ≤ 5 business days | Finance |

| Payment batch | Next available payroll/AP batch | Finance |





## 1.2 Required claim fields


Employee ID and cost center

Expense date and merchant

Amount and currency

Business purpose

Expense category

Project/customer code where applicable

Receipt reference

Attendees for hospitality claims


# 2. Receipt and Evidence Rules



## 2.1 Receipt thresholds





| Expense | Evidence requirement |

| --- | --- |

| ≤ INR 1,000 | Receipt preferred; category controls still apply |

| > INR 1,000 | Receipt mandatory |

| Travel ticket | Ticket/invoice mandatory |

| Hotel | Hotel invoice mandatory |

| Client hospitality | Receipt + attendees + business purpose |

| Software subscription | Invoice + subscription period |





## 2.2 Missing receipts


Employee submits a missing-receipt explanation within 5 business days of Finance request.

The explanation must state merchant, date, amount, business purpose and reason the receipt is unavailable.

Repeated missing-receipt claims may be rejected even when individual claims are otherwise eligible.

Finance may request alternative evidence such as card statement or booking record.


## 2.3 Duplicate prevention


Finance checks claims against prior submissions using employee, merchant, date, amount and reference identifiers. A duplicate claim is held until the employee confirms whether the records represent separate legitimate transactions.


# 3. Manager Review



## 3.1 Manager checklist


Confirm the business purpose.

Confirm the expense belongs to the employee's cost center/project.

Check that the amount is reasonable and within policy.

Verify the claim is not a duplicate.

Confirm required evidence is attached.

Escalate exceptions rather than approving them informally.


## 3.2 Approval thresholds





| Claim value | Manager | Function budget owner | Finance |

| --- | --- | --- | --- |

| ≤ INR 10,000 | Required | No | Control review |

| INR 10,001–50,000 | Required | Control review |  |

| INR 50,001–2,00,000 | Required | Function head | Required |

| > INR 2,00,000 | Required | Function head | CFO delegate + Finance |





## 3.3 Conflict of interest


A manager must not approve their own expense. When the manager is the claimant, approval routes to the manager's designated next-level approver.


# 4. Finance Review and Payment



## 4.1 Finance review checks


Policy eligibility and category mapping

Receipt integrity and legibility

Duplicate detection

Tax treatment where relevant

Cost center and budget availability

Approval completeness

Exception documentation


## 4.2 Payment handling





| Payment route | Typical timing | Notes |

| --- | --- | --- |

| Payroll | Monthly cycle | Employee reimbursements linked to payroll |

| Accounts Payable | Scheduled AP run | Used for approved non-payroll cases |

| Urgent payment | Case-based | Finance manager approval required |





## 4.3 Currency conversion


Foreign expenses are converted using the approved corporate card statement rate where available. If a personal card was used, Finance may use the card statement rate or the published corporate conversion method for the transaction date.


## 4.4 Rejected claims


A rejected claim must include a reason code. Employees may correct and resubmit within 15 calendar days. A claim rejected for an ineligible category cannot become eligible merely by changing the category.


# 5. Exceptions, Controls and Audit



## 5.1 Common exception codes





| Code | Meaning | Typical action |

| --- | --- | --- |

| EX01 | Missing receipt | Return for evidence |

| EX02 | Over limit | Exception approval |

| EX03 | Duplicate suspected | Hold + investigation |

| EX04 | Late submission | Finance review |

| EX05 | Unclear business purpose | Manager clarification |

| EX06 | Restricted category | Finance/Compliance review |





## 5.2 Control analytics


Finance reviews monthly spend by employee, merchant, cost center and category.

Claims over INR 50,000 receive enhanced review.

Unusual month-over-month category increases above 35% are reviewed by the budget owner.

Employees with three or more policy exceptions in a rolling quarter may be referred for policy coaching.


## 5.3 Audit retention


Finance retains reimbursement records according to the corporate record-retention schedule. Audit access is restricted and all administrative changes to approved claims are logged.


# 6. FY26 Service Metrics and Operational Examples



## 6.1 Metrics





| Metric | FY26 value |

| --- | --- |

| Claims processed | 8,462 |

| Median submission-to-payment time | 6.1 business days |

| Manager SLA attainment | 91.8% |

| Finance SLA attainment | 93.4% |

| Claims paid without correction | 86.7% |

| Duplicate detection rate | 1.49% |

| Foreign-currency claims | 742 |

| Average claim value | INR 2,210 |





## 6.2 Worked examples


Example A: An employee submits INR 4,800 for a domestic hotel stay with invoice and approved travel request. The manager can approve; Finance verifies category, dates and evidence.

Example B: An employee submits INR 58,000 for equipment without prior procurement approval. Finance returns the claim because the amount exceeds the normal threshold and procurement controls were bypassed.

Example C: Two claims have the same merchant, date and amount but different receipt references. Finance holds the second claim for duplicate investigation rather than automatically rejecting it.


## Document control


NC-FIN-REIM-2026-08 | Version 3.4 | Next review 31 Jul 2027.
