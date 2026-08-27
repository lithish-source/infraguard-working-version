# Admin Manual

This guide is for **administrators** of InfraGuard — municipal officials, infrastructure managers, and system operators who triage citizen reports and coordinate response.

## Table of Contents
1. [Logging In](#logging-in)
2. [Admin Dashboard Overview](#admin-dashboard-overview)
3. [Report Management](#report-management)
4. [Severity Overrides](#severity-overrides)
5. [Team Assignment](#team-assignment)
6. [Status Workflow](#status-workflow)
7. [Analytics Deep-Dive](#analytics-deep-dive)
8. [Priority Recomputation](#priority-recomputation)
9. [Notifications & Alerts](#notifications--alerts)
10. [Audit Trail](#audit-trail)
11. [Common Workflows](#common-workflows)
12. [Best Practices](#best-practices)

---

## Logging In

1. Navigate to the InfraGuard URL
2. Click **"Sign In"**
3. Use the admin credentials provided by your system administrator
   - Default: `admin@infraguard.gov` / `Admin@12345`
   - **⚠️ Change this immediately in production** via environment variables
4. You'll be redirected to the Admin Dashboard

> 🔒 Admin accounts have full access to all reports, analytics, and management features. Use a strong, unique password and never share credentials.

---

## Admin Dashboard Overview

The dashboard (`/admin`) gives you a real-time snapshot of the entire system.

### Top Metrics (8 KPI cards)

| Card | What it tells you |
|---|---|
| **Total Reports** | All reports ever submitted |
| **Pending** | Reports with status "Reported" — awaiting review |
| **Verified** | Reports confirmed by community consensus |
| **Resolved** | Reports with completed repairs |
| **Critical Incidents** | Reports with Critical severity — needs immediate attention |
| **Total Citizens** | Registered user count |
| **Verifications** | Total crowd-validation actions |
| **Avg Response Time** | Mean hours from report → resolution |

### Critical Alert Banner

When `critical_incidents > 0`, a purple-red banner appears at the top:
> 🚨 **X critical incidents need attention** — Immediate response recommended within 2 hours.

Click **"View Critical →"** to filter the report management page to critical incidents only.

### Charts

| Chart | What it shows |
|---|---|
| **Severity Distribution** (doughnut) | How reports split across Low/Moderate/High/Critical |
| **Monthly Trend** (line) | Reports vs resolved over last 6 months |
| **Damage Categories** (bar) | Total vs critical per infrastructure type |
| **District Analytics** (bar) | Reports / critical / resolved per district |

### Top Critical Reports

The bottom of the dashboard lists the 5 highest-priority critical incidents, each clickable for full details.

### Action Buttons

- **🔄 Recompute Priorities** — refreshes the time-urgency component for all open reports. Useful at the start of each shift.
- **Manage Reports →** — jump to the Report Management page

---

## Report Management

The Report Management page (`/admin/reports`) is your primary workspace.

### Filtering Reports

Use the filter bar at the top:
- **Search** — by title, description, or reference code
- **Status** — Reported / Verified / Assigned / In Progress / Resolved / Rejected
- **Severity** — Low / Moderate / High / Critical
- **Sort** — by priority (default), newest, oldest, or severity

### Selecting a Report

Click any report in the left list. The right panel shows:
- Report summary (title, severity, status, description)
- Reporter info, timestamp, verification count, priority score
- Three action forms (see below)

### Pagination

20 reports per page. Use **"← Prev"** / **"Next →"** at the bottom.

---

## Severity Overrides

The AI severity assessment is good but not perfect. You can override it based on:
- In-person inspection findings
- Expert judgment
- Photo quality issues that misled the AI

### How to override

1. Select a report
2. In the right panel, find **"Override Severity"**
3. Select the new severity (Low/Moderate/High/Critical)
4. Add a **reason** in the notes field (e.g. "Inspector confirmed crack is superficial")
5. Click **"Override Severity"**

### What happens

- The `final_severity` field is set (this takes precedence over `ai_severity`)
- A new `priority_score` is computed using the overridden severity
- An audit log entry is created in `admin_actions` with `action='severity_override'`, `previous_value`, `new_value`, and your notes
- The reporter receives a notification

---

## Team Assignment

Assign a response team to a report to begin physical repair work.

### Quick Assign

1. Select a report
2. In the right panel, find **"Quick Assign Team"**
3. Type the team name (e.g. "Team Alpha", "Municipal Crew B")
4. Add optional notes
5. Click **"Assign Team"**

### What happens

- The report's `assigned_team` field is set
- If the report was in "Reported" or "Verified" status, it's auto-promoted to "Assigned"
- A notification is sent to the original reporter

---

## Status Workflow

Reports flow through these statuses:

```
Reported → Verified → Assigned → In Progress → Resolved
   ↓
Rejected
```

### Updating status

1. Select a report
2. In the right panel, find **"Update Status"**
3. Select the new status from the dropdown
4. Optionally update the assigned team
5. Add resolution notes (required when marking as "Resolved")
6. Click **"Update Status"**

### Status meanings

| Status | Meaning | Trigger |
|---|---|---|
| **Reported** | Newly submitted, awaiting review | Default on creation |
| **Verified** | Community consensus reached (3+ verifications) OR admin manually verifies | Auto-promoted or admin action |
| **Assigned** | A response team has been named | Admin assigns team |
| **In Progress** | Repair work is actively underway | Admin updates status |
| **Resolved** | Repair completed | Admin updates + adds resolution notes |
| **Rejected** | False report or invalid | Admin action (use sparingly) |

### Resolving a report

When marking as "Resolved":
- The `resolved_at` timestamp is set automatically
- Add resolution notes describing what was done (e.g. "Pothole filled with cold-mix asphalt")
- The reporter receives a "Report status updated" notification
- The report stops appearing in priority queues

### Rejecting a report

Use "Rejected" only when:
- The report is clearly false (no damage exists)
- The photo is irrelevant (e.g. landscape, selfie)
- The report is a duplicate of an existing one

For duplicates, prefer to verify and resolve the original rather than reject.

---

## Analytics Deep-Dive

The Analytics page (`/admin/analytics`) provides deeper insights.

### Sections

1. **Top metrics** — avg/min/max response time, citizen engagement stats
2. **Charts grid** — severity distribution, 12-month trend, category distribution, district comparison
3. **🔥 Vulnerability Heatmap** — all reports as a heatmap, weighted by severity. Hot zones indicate areas needing systemic intervention.
4. **🔁 Repeat Incident Detection** — clusters of reports within 500m of each other for the same infrastructure type. Indicates recurring issues that need root-cause analysis.
5. **👥 Citizen Participation** — registered / reported / verified counts, average verifications per report

### Using analytics for resource allocation

- **High repeat-incident clusters** → schedule preventive maintenance, not just reactive repair
- **Districts with high critical counts but low resolved counts** → allocate more crews
- **Low citizen participation in a district** → run awareness campaigns
- **Categories with rising monthly trends** → budget for that infrastructure type next fiscal year
- **Long avg response times** → review team capacity and dispatch protocols

---

## Priority Recomputation

Priority scores change over time because of the **time-urgency component** (older reports → higher urgency).

### When to recompute

- **Start of each shift** — refresh time-urgency for all open reports
- **After bulk status updates** — ensures the queue reflects current state
- **Before resource allocation meetings** — gives you the latest rankings

### How to recompute

1. On the Admin Dashboard, click **"🔄 Recompute Priorities"**
2. The system iterates all open (non-Resolved, non-Rejected) reports
3. For each, it computes a fresh `PriorityScore` row with current time-urgency
4. A toast notification shows: `"Recomputed priorities for N open reports."`

> 💡 This operation is O(N) — for 1000 reports it takes ~5 seconds. Safe to run anytime.

---

## Notifications & Alerts

### Citizen notifications (automatic)

The system sends these automatically:
- Report submission confirmation
- Verification received on their report
- Status changes (verified, assigned, in progress, resolved)
- Severity override notification

### Admin alerts

The **critical alert banner** on the dashboard warns when:
- Any report has Critical severity AND status is "Reported" or "Verified"

For production, configure external alerts:
- Slack/Teams webhook for new Critical reports
- Email digest of unresolved Critical incidents every 4 hours
- SMS to on-call manager for reports older than 2 hours with Critical severity

---

## Audit Trail

Every admin action is logged in the `admin_actions` table:

| Field | Example |
|---|---|
| `admin_id` | Your user ID |
| `report_id` | Affected report |
| `action` | `status_change`, `severity_override`, `assign_team` |
| `previous_value` | "Reported" |
| `new_value` | "Verified" |
| `notes` | "Inspector confirmed damage" |
| `created_at` | 2026-08-11 14:23:00 |

### Querying the audit log

```sql
SELECT admin_id, report_id, action, previous_value, new_value, notes, created_at
FROM admin_actions
WHERE report_id = 42
ORDER BY created_at DESC;
```

This is essential for:
- Compliance audits
- Investigating disputed resolutions
- Training new admins on past decisions

---

## Common Workflows

### Workflow 1: Morning Triage

1. Log in → Admin Dashboard
2. Click **"🔄 Recompute Priorities"** — refresh overnight time-urgency
3. Check the **critical alert banner** — address critical incidents first
4. Click **"Manage Reports →"**
5. Filter by status = "Reported" — review new submissions
6. For each new report:
   - Look at the photo and AI assessment
   - If AI seems wrong → override severity
   - If genuine → assign a team (auto-promotes to "Assigned")
   - If false → mark as "Rejected" with reason

### Workflow 2: Mid-Shift Progress Update

1. Filter by status = "Assigned"
2. For each report where the team has finished work:
   - Update status to "In Progress" or "Resolved"
   - Add resolution notes
3. Filter by status = "In Progress"
4. For each report where work is complete:
   - Update status to "Resolved" with notes

### Workflow 3: End-of-Day Review

1. Open the Analytics page
2. Check today's resolved count vs new reports
3. Review the **repeat incident clusters** — flag systemic issues
4. Check **district analytics** — any district overwhelmed?
5. Export any data needed for daily reports (use the API)

### Workflow 4: Critical Incident Response

1. Dashboard shows **"3 critical incidents need attention"**
2. Click **"View Critical →"**
3. Sort by priority score (default)
4. Open the top-priority report
5. Verify the AI assessment (override if needed)
6. Immediately assign the closest team
7. Update status to "Assigned"
8. If life-threatening, contact emergency services directly (InfraGuard doesn't replace 911)

---

## Best Practices

### DO

- ✅ **Override severity when AI is wrong** — your judgment as a domain expert is valued
- ✅ **Always add notes** to status changes and overrides — future auditors will thank you
- ✅ **Use "Verified" sparingly** — let the crowd verify; only manually verify when you've inspected in person
- ✅ **Reject only genuine false reports** — citizens lose trust if legitimate reports are rejected
- ✅ **Recompute priorities at shift changes** — keeps the queue fresh
- ✅ **Monitor repeat incident clusters** — they indicate systemic issues, not one-off damage

### DON'T

- ❌ **Don't bulk-resolve reports** without verification — each deserves individual review
- ❌ **Don't change severity without inspecting the photo** — the AI may be right
- ❌ **Don't leave reports in "Assigned" for days** — either start work or unassign
- ❌ **Don't ignore critical alerts** — they exist for a reason
- ❌ **Don't share your admin credentials** — request separate admin accounts for each team member

---

## FAQ for Admins

**Q: How do I create additional admin accounts?**  
A: Currently, admins are created via database seed or SQL. For production, add an admin-only "user management" page. As a workaround:
```sql
UPDATE users SET role = 'admin' WHERE email = 'newadmin@example.com';
```

**Q: Can I delete a report?**  
A: No — reports are immutable for audit trail. Use "Rejected" status instead. If a report contains sensitive info (e.g. license plate visible), contact the dev team to redact the image.

**Q: How do I export reports for external analysis?**  
A: Use the API:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/reports?page_size=100" > reports.json
```
Or query the database directly:
```sql
COPY (SELECT * FROM v_report_summary) TO '/tmp/reports.csv' WITH CSV HEADER;
```

**Q: The AI confidence is low (e.g. 0.55). Should I trust it?**  
A: Treat low-confidence assessments as a starting point. Always inspect the photo yourself. The AI is most reliable above 0.75 confidence.

**Q: How often should I recompute priorities?**  
A: At minimum, once per shift. If your team works 24/7, set up a cron job to recompute hourly:
```bash
0 * * * * curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/v1/admin/priority/recompute
```

**Q: What's the difference between `ai_severity` and `final_severity`?**  
A: `ai_severity` is the AI's prediction. `final_severity` is your override (if any). The system uses `final_severity` if set, otherwise falls back to `ai_severity`. Both are preserved for auditability.

---

## Incident Response Escalation Matrix

| Severity | Reports With | Initial Response | Escalate To |
|---|---|---|---|
| Critical | Bridge/structure failure, water main burst | < 2 hours | Municipal engineer + emergency services |
| High | Major pothole, signal malfunction | < 6 hours | District maintenance crew |
| Moderate | Streetlight out, drain clog | < 24 hours | Routine maintenance queue |
| Low | Park bench damage, minor cracks | < 72 hours | Next scheduled maintenance cycle |
| Minimal | Cosmetic issues | < 7 days | Backlog |

> ⚠️ InfraGuard is a **reporting and prioritization tool**, not a replacement for emergency services. For life-threatening situations, always call emergency services directly.

---

## Support

- **Bug reports** → project issue tracker
- **Feature requests** → project issue tracker with "enhancement" label
- **Training new admins** → walk them through this manual + sandbox environment
- **Data exports / custom reports** → contact the development team
