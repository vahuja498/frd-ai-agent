# Functional Requirement Document

## Customer Portal v2
### Version: 1.0 | Date: 2026-03-19 | Status: Draft | Prepared by: FRD AI Agent


---

## 1. Business Objective
* [2-4 sentence summary of what the project aims to achieve and why](#business-objective)
* Expected to reduce HR admin workload by 30% and improve employee satisfaction scores.

### Description
This Customer Portal V2 aims to enhance the employee self-service experience, reducing administrative burden on HR teams while improving employee satisfaction. The portal will enable employees to manage their HR information, view payslips, apply for leave, update personal details, and more without requiring direct contact with the HR team.


---

## 2. Scope
### In Scope:
* Employee authentication via Azure AD Single Sign-On (SSO)
* Employee dashboard (leave balance, upcoming holidays, recent payslips)
* Leave application and approval workflow
* Payslip viewing and PDF download (integration with Sage Payroll)
* Personal details update (address, emergency contact, bank details)
* Manager approval workflow for leave requests
* Email notifications for leave approval/rejection

### Out of Scope:
* Payroll processing or calculation
* Recruitment or onboarding
* Performance management
* Mobile application (Phase 2)

---

## 3. Stakeholders
| Name / Role | Type | Responsibility |
|---|---|---|
| Emma Clarke | Product Owner | Requirements sign-off, UAT |
| Michael Banks | HR Director | Business process definition |
| Raj Patel | IT Manager | Infrastructure, SSO config |

---

## 4. Assumptions
* Azure AD is already configured and employee accounts exist.
* Sage Payroll API supports read access for payslip data.
* All employees have corporate email addresses.

---

## 5. Functional Requirements

### FR-01: Employee Login via SSO
#### Description:
* Employees must authenticate using Azure AD Single Sign-On (SSO).
* No separate username/password shall be created.

#### Actor:
* Employee

#### Priority:
* High

#### Source:
* Explicit

#### Acceptance Criteria:

1. Employee clicks "Sign In" and is redirected to Azure AD login page
2. On successful Azure AD authentication, employee is redirected to the portal dashboard
3. Failed authentication displays an appropriate error message

### FR-02: View Employee Dashboard
#### Description:
* Upon login, employee sees a personalised dashboard showing:
	+ Leave balance
	+ Upcoming holidays
	+ Last 3 payslips
	+ Pending actions

#### Actor:
* Employee

#### Priority:
* High

#### Source:
* Explicit

#### Acceptance Criteria:

1. Dashboard loads within 2 seconds
2. Leave balance reflects current approved/pending leave
3. Payslip section shows most recent 3 months

### FR-03: Apply for Leave
#### Description:
* Employee can submit a leave request specifying:
	+ Leave type
	+ Start date
	+ End date
	+ Optional notes
* Request is routed to their line manager for approval.

#### Actor:
* Employee

#### Priority:
* High

#### Source:
* Explicit

#### Acceptance Criteria:

1. Employee can select from available leave types (Annual, Sick, Unpaid)
2. System validates leave balance before submission
3. Manager receives email notification within 5 minutes of submission
4. Approved leave appears in shared team calendar

### FR-04: Update Personal Details
#### Description:
* Employees can update their home address, emergency contact, and bank details.
* Changes require re-authentication (step-up auth) for bank detail updates.

#### Actor:
* Employee

#### Priority:
* Medium

#### Source:
* Explicit

#### Acceptance Criteria:

1. Address and emergency contact changes save immediately
2. Bank detail changes require password re-entry before saving
3. All changes generate an audit log entry

### FR-05: View Payslips
#### Description:
* Employees can view a history of their payslips and download individual payslips as PDF documents.
* Data sourced from Sage Payroll API.

#### Actor:
* Employee

#### Priority:
* Medium

#### Source:
* Explicit

#### Acceptance Criteria:

1. Payslips are listed in reverse chronological order
2. Each payslip shows date, gross pay, net pay, and deductions summary
3. PDF download completes within 3 seconds
4. Payslips are accessible for the previous 24 months

### FR-06: Update Manager Details
#### Description:
* Employees can update their manager's contact details.
* Changes require re-authentication (step-up auth) for bank detail updates.

#### Actor:
* Employee

#### Priority:
* Medium

#### Source:
* Explicit

#### Acceptance Criteria:

1. Address and emergency contact changes save immediately
2. Bank detail changes require password re-entry before saving
3. All changes generate an audit log entry

---

## 6. Non-Functional Requirements

| ID | Category | Description | Metric / Target |
|---|---|---|---|
| NFR-01: Performance | Category: Performance | Pages must load within 3 seconds under normal load | p95 page load time < 3s with 200 concurrent users |

| ID | Category | Description | Metric / Target |
|---|---|---|---|
| NFR-02: Availability | Category: Availability | System must be available 99.5% of the time excluding planned maintenance | Monthly uptime >= 99.5%, maintenance windows < 4 hours/month |

| ID | Category | Description | Metric / Target |
|---|---|---|---|
| NFR-03: Security | Category: Security | All data encrypted in transit and at rest. OWASP Top 10 compliance required | Zero critical security vulnerabilities in pre-launch penetration test |

| ID | Category | Description | Metric / Target |
|---|---|---|---|
| NFR-04: GDPR Compliance | Category: Compliance | All personal data must be handled in accordance with GDPR. Employee data retained for maximum 7 years after employment end | GDPR audit passed prior to go-live |

---

## 7. Business Rules

### BR-01: An employee cannot approve their own leave request.
#### Description:
* Leave cannot be approved retroactively for dates in the past.

#### Actor:
* Employee

#### Priority:
* High

#### Source:
* Explicit

#### Acceptance Criteria:

1. Employee can select from available leave types (Annual, Sick, Unpaid)
2. System validates leave balance before submission
3. Manager receives email notification within 5 minutes of submission
4. Approved leave appears in shared team calendar

### BR-02: Leave cannot be applied retroactively for dates in the past.
#### Description:
* Leave cannot be applied to dates that have already passed.

#### Actor:
* Employee

#### Priority:
* High

#### Source:
* Explicit

#### Acceptance Criteria:

1. Employee can select from available leave types (Annual, Sick, Unpaid)
2. System validates leave balance before submission
3. Manager receives email notification within 5 minutes of submission
4. Approved leave appears in shared team calendar

### BR-03: Sick leave does not require manager approval but does trigger an HR notification.
#### Description:
* Leave applies directly to the employee's own record.

#### Actor:
* Employee

#### Priority:
* High

#### Source:
* Explicit

#### Acceptance Criteria:

1. Employee can select from available leave types (Annual, Sick, Unpaid)
2. System validates leave balance before submission
3. Manager receives email notification within 5 minutes of submission

### BR-04: An employee with zero leave balance cannot submit an annual leave request.
#### Description:
* Leave applies directly to the employee's own record.

#### Actor:
* Employee

#### Priority:
* High

#### Source:
* Explicit

#### Acceptance Criteria:

1. Employee can select from available leave types (Annual, Sick, Unpaid)
2. System validates leave balance before submission
3. Manager receives email notification within 5 minutes of submission

### BR-05: Bank detail changes take effect from the next payroll run, not immediately.
#### Description:
* Changes generate an audit log entry.

#### Actor:
* Employee

#### Priority:
* Medium

#### Source:
* Explicit

#### Acceptance Criteria:

1. Address and emergency contact changes save immediately
2. All changes generate an audit log entry