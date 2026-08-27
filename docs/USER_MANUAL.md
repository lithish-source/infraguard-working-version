# User Manual (Citizen Guide)

Welcome to InfraGuard! This guide walks you through reporting infrastructure damage and tracking its resolution.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Registering an Account](#registering-an-account)
3. [Submitting a Damage Report](#submitting-a-damage-report)
4. [Tracking Your Reports](#tracking-your-reports)
5. [Verifying Other Reports](#verifying-other-reports)
6. [Using the Damage Map](#using-the-damage-map)
7. [Managing Notifications](#managing-notifications)
8. [Settings & Profile](#settings--profile)

---

## Getting Started

InfraGuard is a community platform where you can:
- 📸 Report damaged infrastructure (roads, bridges, streetlights, water pipelines, etc.)
- 🤖 Get instant AI-powered severity assessment
- 👥 Verify reports from other citizens to build community consensus
- 🗺️ View all damage reports on an interactive map
- 📊 Track the status of your reports until resolution

**You don't need any technical knowledge.** If you can use a smartphone camera and fill out a form, you can use InfraGuard.

---

## Registering an Account

1. Go to the InfraGuard website (e.g. http://localhost:5173)
2. Click **"Get Started"** or **"Register"**
3. Fill in the registration form:
   - **Full Name:** Your real name (e.g. "Jane Doe")
   - **Email:** A valid email you check regularly
   - **Phone:** Optional, but helps authorities contact you if needed
   - **Password:** At least 8 characters with one uppercase letter and one digit (e.g. `MyP@ssw0rd`)
4. Click **"Create Account"**
5. You'll be automatically logged in and taken to your dashboard

> 💡 **Tip:** Use a strong, unique password. Your account holds your report history.

---

## Submitting a Damage Report

### When to report
Report any damage to public infrastructure that you observe:
- Potholes, cracks, subsidence on roads
- Cracks, corrosion, or structural issues on bridges
- Broken or non-functional streetlights
- Burst or leaking water pipelines
- Malfunctioning traffic signals
- Damaged footpaths, drainage covers, public buildings, park equipment

### How to submit

1. From any page, click **"+ New Report"** (in the sidebar or dashboard)

2. **Fill in the form:**
   - **Title:** Brief summary (e.g. "Large pothole on MG Road near signal")
   - **Category:** Select the type of infrastructure (Road, Bridge, Streetlight, etc.)
   - **District:** Optional — auto-detected if you skip
   - **Description:** What you observed, when, and any safety concerns
   - **Location:** Click **"📍 Detect My Location"** — your browser will ask permission. Allow it to auto-fill latitude/longitude. Alternatively, type coordinates manually.
   - **Address:** Optional landmark or street name
   - **Photos:** Upload 1-5 photos of the damage (JPG, PNG, or WEBP, max 10MB each)

3. Click **"Submit Report"**

4. **Wait a few seconds** — our AI engine will:
   - Analyze your primary photo
   - Estimate damage severity (Low/Moderate/High/Critical)
   - Calculate a priority score based on severity, location, and surrounding context

5. You'll be redirected to the **Report Details** page showing:
   - The AI's severity assessment with confidence score
   - The detected damage type (e.g. "Pothole", "Surface Crack")
   - The priority score and recommended response time
   - A unique reference code (e.g. `RPT-20260811-A1B2C3`) for tracking

### Photo tips for better AI results

- ✅ **Take photos in good lighting** — daylight is best
- ✅ **Get close enough** to clearly see the damage
- ✅ **Capture the full extent** — pan back if needed to show surrounding context
- ✅ **Hold the camera steady** to avoid blur
- ❌ Avoid photos with heavy shadows or glare
- ❌ Don't upload photos that don't show damage (landscapes, selfies, etc.)

---

## Tracking Your Reports

1. Click **"My Reports"** in the sidebar
2. You'll see all your reports with status tabs:
   - **All** — every report you've submitted
   - **Reported** — newly submitted, awaiting review
   - **Verified** — confirmed by community consensus (3+ verifications)
   - **Assigned** — a response team has been assigned
   - **In Progress** — repair work is underway
   - **Resolved** — fix completed

3. Click any report to see full details, including:
   - AI severity assessment
   - Priority score breakdown
   - Crowd verifications
   - Status history
   - Assigned team and resolution notes (once resolved)

### Status flow

```
Reported → Verified → Assigned → In Progress → Resolved
   ↓
Rejected (if false)
```

---

## Verifying Other Reports

Community verification helps filter false reports and prioritize real ones.

1. Open the **Damage Map** or any report's detail page
2. On a report you didn't create, you'll see a **"Verify This Report"** form
3. Fill in:
   - **Severity Vote** (optional): Your assessment of the severity
   - **Comment** (optional): Add context (e.g. "Confirmed — I drive past this daily")
   - **Additional Photo** (optional): Upload your own photo of the same damage
4. Click **"✓ Confirm"** if the report is genuine, or **"✗ Flag"** if it's inaccurate

### What happens when you verify?

- The report's **credibility score** increases
- The **verification count** goes up
- If 3+ citizens verify a report, it's **auto-promoted to "Verified"** status
- The priority score is **recomputed** — verifications boost priority
- The original reporter gets a notification

> ⚠️ You can only verify each report once. You cannot verify your own reports.

---

## Using the Damage Map

1. Click **"Damage Map"** in the sidebar
2. You'll see a map with colored markers:
   - 🟢 **Green** = Low severity
   - 🟡 **Amber** = Moderate severity
   - 🔴 **Red** = High severity
   - 🟣 **Purple** = Critical severity

3. **Click any marker** to see a popup with:
   - Report title and reference code
   - Severity and status badges
   - Primary photo
   - Verification count
   - Priority score
   - Link to full report details

4. **Filters** (top of the map):
   - **District** — filter by administrative area
   - **Category** — filter by infrastructure type
   - **Severity** — show only Critical, High, etc.
   - **Status** — show only Resolved, Reported, etc.
   - **🔥 Heatmap toggle** — show density heatmap instead of markers

5. **Markers cluster automatically** when zoomed out — click a cluster to zoom in

6. **Summary chips** above the map show counts of total/critical/high/resolved reports matching your filters

---

## Managing Notifications

You'll receive notifications when:
- ✅ Your report is submitted successfully
- 👥 Someone verifies your report
- 🔄 Your report's status changes (verified, assigned, in progress, resolved)
- 🚨 A critical alert is issued (admin-only notifications)

### Viewing notifications
1. Click **"Notifications"** in the sidebar (the bell icon shows unread count)
2. Unread notifications are highlighted in blue
3. Click any notification to:
   - Mark it as read
   - Jump to the related report

### Mark all as read
Click **"Mark all read"** at the top of the notifications page.

---

## Settings & Profile

Click **"Settings"** in the sidebar to:
- Update your full name and phone number
- View your email (cannot be changed)
- Switch between light and dark themes
- Sign out of your account

### Dark mode
InfraGuard supports both light and dark themes. Toggle via the **"🌙 Dark / ☀️ Light"** button in the sidebar bottom or in Settings. Your choice is remembered across sessions.

---

## Frequently Asked Questions

**Q: Do I need to install any software?**  
A: No. InfraGuard runs in any modern web browser (Chrome, Firefox, Safari, Edge).

**Q: Can I report anonymously?**  
A: Currently no — you must be logged in. This prevents spam and false reports. Your identity is only visible to administrators.

**Q: What if I don't have GPS?**  
A: You can manually enter latitude/longitude coordinates. Use Google Maps to find them — right-click any location → "What's here?" → copy the coordinates.

**Q: How accurate is the AI severity assessment?**  
A: The AI gives a confidence score (55%-95%). For high-stakes decisions, authorities always do an in-person inspection. The AI's role is to prioritize, not replace human judgment.

**Q: What happens to false reports?**  
A: Other citizens can flag your report. If multiple citizens flag it, an admin may mark it as "Rejected". Repeated false reports may lead to account suspension.

**Q: Can I edit or delete my report after submission?**  
A: Currently no — once submitted, reports are immutable for audit trail integrity. Contact an admin if you need a report removed.

**Q: How long until my report is resolved?**  
A: It depends on severity and priority:
- Critical: within 2 hours (immediate response)
- High: within 6 hours
- Moderate: within 24 hours
- Low: within 72 hours
- Minimal: within 7 days

Actual resolution times depend on municipal resources.

---

## Need Help?

- **Forgot password?** Contact your administrator (currently no self-service reset)
- **Found a bug?** Report it via the project's issue tracker
- **Have suggestions?** Feedback is welcome — the platform evolves based on citizen input

Thank you for being an active citizen reporter! 🛡️
