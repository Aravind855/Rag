# NexaCore Access Control Standard

**Document ID:** NC-SEC-ACL-2026-08  
**Version:** 4.6  
**Effective:** 01 August 2026  
**Owner:** Security Engineering  
**Classification:** Internal / Confidential

> Synthetic private-company data for RAG evaluation. Not sourced from a real organization.

## 1. Access Control Model

NexaCore uses role-based access control (RBAC) with attribute checks where resource context requires them. Access follows **least privilege**, **need to know**, and **separation of duties**.

### 1.1 Core principles

1. Every production permission must map to a business or operational requirement.
2. Access should be granted to roles/groups rather than directly to individuals when the platform supports groups.
3. Privileged access requires MFA and enhanced logging.
4. Access reviews must verify actual need, not merely manager ownership.
5. Dormant accounts and stale permissions must be removed or disabled.

## 2. Role Classes

| Role | Typical scope | Privilege |
|---|---|---|
| Employee | Corporate applications | Standard |
| Manager | Team reporting/workflows | Elevated business |
| Application Admin | Specific application | Privileged |
| Platform Engineer | Infrastructure services | Privileged |
| Security Analyst | Security systems | Privileged |
| Finance Admin | Finance systems | Restricted business |
| Break-glass Admin | Emergency production recovery | Emergency privileged |

## 3. Joiner / Mover / Leaver Controls

### Joiner

HR creates the identity record. Standard access is provisioned based on department and role. Additional access requires application-owner approval.

Target: **4 business hours** from approved provisioning event.

### Mover

When an employee changes department or role, previous access must be reviewed rather than assuming the old role remains valid.

Target: **4 business hours** for standard role changes.

### Leaver

Access is disabled according to HR termination timing. Immediate termination/security-risk cases require immediate revocation after notification.

## 4. Privileged Access

Privileged accounts must:

- Use MFA.
- Use named identities.
- Avoid shared credentials.
- Be logged.
- Have an owner.
- Be reviewed quarterly.
- Use temporary elevation where supported.

### 4.1 Privileged session controls

| Control | Standard |
|---|---|
| Inactivity timeout | 15 minutes |
| MFA | Required |
| Session logging | Required where platform supports it |
| Access review | Quarterly |
| Emergency access review | Within 1 business day |
| Credential rotation | Per platform/security standard |

## 5. Production Access

Production access is divided into:

- Read-only diagnostic access
- Operational write access
- Deployment access
- Security administration
- Database administration

A developer does not automatically receive production database write access merely because they can deploy application code.

## 6. Approval Matrix

| Access type | Requester | Approver |
|---|---|---|
| Standard application | Employee | Manager + application owner |
| Sensitive application | Employee | Manager + data/application owner |
| Production read | Engineer | Manager + service owner |
| Production write | Engineer | Service owner + security/authorized approver |
| Privileged admin | Engineer/Admin | Manager + system owner |
| Emergency access | On-call responder | Emergency mechanism; retrospective approval |

## 7. Access Review

Quarterly certification covers:

- Active users
- Privileged users
- Group membership
- Service accounts
- Dormant accounts
- Excessive permissions
- Orphaned ownership

### Review thresholds

Accounts inactive for **45 days** are candidates for review. Privileged accounts inactive for **30 days** require explicit validation.

## 8. Service Accounts

Every service account must have:

- Unique owner
- Business purpose
- System scope
- Credential rotation method
- Expiry/review date
- Non-human identity classification

Service accounts should not be used for interactive human login.

## 9. Break-Glass Access

Break-glass access is restricted to emergency recovery. It must:

1. Be used only when normal access is unavailable or insufficient.
2. Generate an audit record.
3. Be reviewed within 1 business day.
4. Have credentials protected separately from normal administration.
5. Be rotated after use where the credential model requires it.

## 10. Access Metrics

FY26 reference metrics:

| Metric | Value |
|---|---:|
| Quarterly privileged review completion | 100% |
| Standard access requests within SLA | 94.1% |
| Dormant accounts disabled | 287 |
| Access exceptions | 18 |
| Emergency privileged events | 34 |
| Orphaned service accounts found | 7 |

## 11. Exceptions

An exception requires a reason, affected identity/system, risk, compensating control, owner, approver and expiry date. Standard exception duration is **90 days**.

## 12. Audit Evidence

Security may request:

- Approval record
- Access-change ticket
- Identity-provider event
- Application role assignment
- Privileged session record
- Review certification
- Exception record

Document review cadence: quarterly.
