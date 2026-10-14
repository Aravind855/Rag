---
id: nc.engineering.deployment_guide
title: NexaCore Deployment Guide
type: Playbook
description: 'NexaCore uses an environment-separated delivery model: Development →
  Test → Staging → Production.'
tags:
- engineering
- playbook
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
- id: deployment_guide-source
  resource: /Datasource/engineering/deployment_guide.pdf
  title: Source Document deployment_guide.pdf
---

<!-- File: deployment_guide.pdf | Category: engineering | Pages: 6 | Chunks: 1 -->
<!-- Total Cleaned Chars: 6,282 -->

# **NexaCore Deployment Guide**

### **Version 3.7 | Engineering Production Delivery**

**Owner:** Platform Engineering **Effective:** 01 Aug 2026 **Review:** 31 Jul 2027

## **1. Deployment Model**

NexaCore uses an environment-separated delivery model: Development → Test → Staging → Production. Promotion is controlled by CI/CD policies rather than manual source copying.

### **1.1 Environment purpose**

|**Environment**|**Purpose**|**Data**|**Deployment authority**|
|---|---|---|---|
|Development|Feature development|Synthetic / masked|Developer|
|Test|Automated integration testing|Synthetic|CI|
|Staging|Production-like validation|Masked / approved test|Release owner|
|Production|Customer workloads|Live|Release owner + controls|


### **1.2 Release trains**

- Standard production releases are scheduled Tuesday–Thursday during approved release windows.

- Friday production releases require explicit engineering manager approval unless they are emergency/security fixes.

- Tier-1 services require a named release owner and on-call engineer.

- Production deployment windows are normally 11:00–16:00 IST for standard changes.

### **1.3 Change classes**

Normal changes follow the standard pipeline. Emergency changes use the incident/hotfix workflow and require retrospective documentation within one business day.


Page 1

## **2. CI/CD Pipeline and Gates**

### **2.1 Standard pipeline**

|**Stage**|**Gate**|**Failure action**|
|---|---|---|
|Source checkout|Commit integrity|Stop|
|Build|Compilation/package success|Stop|
|Unit tests|Required suite pass|Stop|
|Static analysis|No blocking findings|Stop or exception|
|Security scan|Severity threshold|Stop or security exception|
|Integration tests|Required suites pass|Stop|
|Artifact publish|Checksum/version recorded|Stop|
|Deploy staging|Health checks|Stop|
|Smoke test|Critical endpoints pass|Stop|
|Production|Approval policy|Controlled promotion|


### **2.2 Build reproducibility**

- Build artifacts must be versioned and traceable to source commit.

- Dependency lock files should be honored in CI.

- Production artifacts should be promoted rather than rebuilt from a different source state.

- Container images must use immutable digests for production deployment.


Page 2

## **3. Production Release Procedure**

### **3.1 Pre-release checklist**

- Confirm change ticket and owner.

- Review automated test results and deployment diff.

- Verify database migration compatibility.

- Confirm monitoring dashboards and alerts.

- Confirm rollback or forward-fix plan.

- Check on-call coverage.

- Communicate customer-impacting maintenance where required.

### **3.2 Deployment sequence**

|**Step**|**Maximum target**|**Required evidence**|
|---|---|---|
|Pre-flight|15 min|Checklist complete|
|Canary|10 min|Health + error metrics|
|Initial rollout|15 min|No regression threshold breach|
|Full rollout|30 min|Service healthy|
|Post-deploy|15 min|Smoke + dashboard review|


### **3.3 Canary stop conditions**

Pause rollout when 5xx error rate increases by more than 1 percentage point above the pre-release baseline for 5 consecutive minutes, p95 latency increases by more than 30%, or a critical health check fails.


Page 3

## **4. Database and Infrastructure Changes**

### **4.1 Database migration rules**

- Prefer backward-compatible expand/contract migrations.

- Large backfills must be throttled and observable.

- Migration duration must be estimated before production.

- Destructive operations require explicit approval and verified backup/restore readiness.

- Application deployment should not depend on a migration completing instantaneously.

### **4.2 Infrastructure changes**

|**Change**|**Required validation**|
|---|---|
|Compute scaling|Capacity + cost estimate|
|Network rule|Security review + connectivity test|
|Storage expansion|Capacity forecast + alert threshold|
|IAM policy|Least privilege review|
|Managed service upgrade|Compatibility + rollback/restore test|


### **4.3 Backup expectations**

Tier-1 production databases target daily full backups plus transaction/log recovery according to service architecture. Restore tests are performed quarterly for Tier-1 systems and semiannually for Tier-2 systems.


Page 4

## **5. Rollback, Incident Response and Recovery**

### **5.1 Rollback decision**

Rollback is preferred when the deployed change is the clear cause of customer impact and the previous artifact remains safe. Forward-fix is preferred when rollback would create data incompatibility or the incident is caused by an irreversible migration.

### **5.2 Severity response**

|**Severity**|**Example**|**Initial response**|
|---|---|---|
|SEV-1|Widespread customer outage / major data risk|≤5 min|
|SEV-2|Material degradation / limited outage|≤15 min|
|SEV-3|Localized issue / workaround exists|≤1 hr|
|SEV-4|Low-impact defect|Next business day|


### **5.3 Recovery objectives**

Reference targets: Tier-1 RTO 60 minutes and RPO 15 minutes; Tier-2 RTO 4 hours and RPO 1 hour. Individual services may have stricter targets documented in their service record.

### **5.4 Post-incident**

Customer-impacting deployment incidents require a timeline, impact assessment, root/contributing factors, corrective actions and named owners. The review target is 3 business days after stabilization.


Page 5

## **6. Deployment Metrics and Governance**

### **6.1 FY26 release snapshot**

|**Metric**|**Value**|
|---|---|
|Production deployments|2,914|
|Successful first-attempt deployments|92.6%|
|Change failure rate|7.4%|
|Median deployment duration|18 min|
|Average rollback time|11 min|
|Tier-1 services using canary rollout|82%|
|Automated smoke-test coverage|91%|
|Deployments outside release window|3.1%|


### **6.2 Release governance**

- Weekly release-health review tracks failed deployments, rollbacks and recurring pipeline failures.

- Monthly production-readiness review checks Tier-1 service ownership and rollback evidence.

- Quarterly disaster-recovery exercise validates selected restore and failover paths.

- Deployment exceptions expire after 30 days unless renewed by the responsible engineering owner.

### **Document control**

Policy ID: NC-ENG-DEP-2026-08 | Version 3.7 | Owner: Platform Engineering | Next review: 31 Jul 2027.


Page 6
