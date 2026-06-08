---
name: jira-flesh-out
description: Fleshes out unresolved Jira tickets in a project with complete, unambiguous acceptance criteria and implementation details targeting a Zero-Context Practitioner. Generates prerequisites, Given/When/Then ACs, verification steps, error scenarios, rollback instructions, and a Fibonacci story point estimate, then writes all content back to each ticket. Dispatches all tickets as parallel agents after a single bulk confirmation. Trigger phrases: "flesh out jira tickets", "detail jira tickets", "write acceptance criteria", "fill in jira tickets", "/jira-flesh-out".
version: 1.10.0
argument-hint: <PROJECT_KEY> [max-tickets] [epics]
allowed-tools:
  - mcp__claude_ai_Atlassian_Rovo__getVisibleJiraProjects
  - mcp__claude_ai_Atlassian_Rovo__searchJiraIssuesUsingJql
  - mcp__claude_ai_Atlassian_Rovo__getJiraIssue
  - mcp__claude_ai_Atlassian_Rovo__getJiraProjectIssueTypesMetadata
  - mcp__claude_ai_Atlassian_Rovo__getJiraIssueTypeMetaWithFields
  - mcp__claude_ai_Atlassian_Rovo__getIssueLinkTypes
  - mcp__claude_ai_Atlassian_Rovo__createIssueLink
  - mcp__claude_ai_Atlassian_Rovo__editJiraIssue
  - mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue
  - mcp__unblocked__context_research
  - mcp__unblocked__context_get_urls
---

# jira-flesh-out

Rewrites unresolved Jira ticket descriptions with complete, copy-pasteable acceptance criteria and implementation guidance. The output targets a Zero-Context Practitioner: someone who understands basic syntax but has zero tribal knowledge of your infrastructure. Every ticket must leave this skill with no ambiguity, no implicit steps, and no room for interpretation.

---

## Phase 1 — Resolve Jira cloud ID

> **⚙️ Configuration required:** Replace the two placeholder values below with your own Jira instance details before using this skill.
> - **`cloudId`**: Call `getAccessibleAtlassianResources` once and copy the `id` field from the response.
> - **`url`**: Your Atlassian site base URL (e.g. `https://yourorg.atlassian.net`).

Use the following hardcoded values — do not call `getAccessibleAtlassianResources` at runtime:

- `cloudId`: `YOUR_CLOUD_ID`  ← replace with your cloudId
- `url` (site base URL): `https://yourorg.atlassian.net`  ← replace with your URL

---

## Phase 2 — Determine the project key, batch limit, and epic filter

Parse the arguments as follows:

- `$1` is always `PROJECT_KEY` (e.g. `ENG`).
- Any numeric argument among `$2`–`$4` is `MAX_TICKETS`. Default to `10` if omitted. Hard cap at `20`.
- If the word `epics` appears anywhere in the arguments (e.g. `/jira-flesh-out ENG epics` or `/jira-flesh-out ENG 5 epics`), set `INCLUDE_EPICS = true`. Otherwise default to `INCLUDE_EPICS = false`.
- If no `PROJECT_KEY` was provided at all, call `getVisibleJiraProjects` with the resolved `cloudId`, display the list (key + name), and ask the user to specify a project.

Tell the user what mode you are running in before fetching:
> "Fetching the newest {MAX_TICKETS} unresolved tickets in {PROJECT_KEY} (epics {included/excluded})."

---

## Phase 2.5 — Discover the Acceptance Criteria field, story points field, link type, and priority names

This phase runs in two batches. **Batch 1** fires three calls in parallel. **Batch 2** fires one call that depends on a Batch 1 result.

### Batch 1 (parallel)

**Issue type IDs** — Call `getJiraProjectIssueTypesMetadata` with the resolved `cloudId` and `PROJECT_KEY`. From the response, find the first non-Epic, non-Subtask issue type (prefer "Story" if present). Store its `id` as `FIELD_DISCOVERY_ISSUETYPE_ID`. If the call fails, set `FIELD_DISCOVERY_ISSUETYPE_ID = null`.

**Link type** — Call `getIssueLinkTypes` with the resolved `cloudId`. Find the link type whose name is exactly `"Relates to"` (case-insensitive). Store its `id` as `RELATES_LINK_TYPE_ID`.

- If `"Relates to"` is not present, use the first available link type and log its name.
- If the call fails or returns no types, set `RELATES_LINK_TYPE_ID = null`. Log: `"No issue link types available — related ticket linking will be skipped."`.

**Priority names** — Call `searchJiraIssuesUsingJql` with:
- JQL: `project = {PROJECT_KEY} AND priority not in ("Uncategorized") ORDER BY updated DESC`
- `fields`: `priority`
- `maxResults`: 5

Extract the distinct `priority.name` values from the results.

- If you see names like `P1`, `P2`, `P3` (number-suffixed with optional prefix): this project uses a custom scheme. Build `PRIORITY_NAME_MAP`: `P1→P1`, `P2→P2`, `P3→P3`, `P4→P4`, `P5→P5`. Store `PRIORITY_FALLBACK_MAP`: `P1→Highest`, `P2→High`, `P3→Medium`, `P4→Low`, `P5→Lowest`.
- If you see names like `Highest`, `High`, `Medium`, `Low`, `Lowest`: standard Jira scheme. Build `PRIORITY_NAME_MAP`: `P1→Highest`, `P2→High`, `P3→Medium`, `P4→Low`, `P5→Lowest`. Store `PRIORITY_FALLBACK_MAP`: `P1→P1`, `P2→P2`, `P3→P3`, `P4→P4`, `P5→P5`.
- If the call fails or returns no results (all tickets are Uncategorized): set `PRIORITY_NAME_MAP`: `P1→P1`, `P2→P2`, `P3→P3`, `P4→P4`, `P5→P5`. Set `PRIORITY_FALLBACK_MAP`: `P1→Highest`, `P2→High`, `P3→Medium`, `P4→Low`, `P5→Lowest`.

### Batch 2 — AC field + Story points field

Wait for Batch 1 to complete, then:

If `FIELD_DISCOVERY_ISSUETYPE_ID` is not null, call `getJiraIssueTypeMetaWithFields` with the resolved `cloudId`, `PROJECT_KEY`, and `FIELD_DISCOVERY_ISSUETYPE_ID`. This returns the full field list for that issue type, including custom field keys and their human-readable names.

Scan the returned fields for two fields:

1. A field whose name contains "acceptance criteria" (case-insensitive). Common keys include `customfield_10014`, `customfield_10016`, or similar.
   - If found, store as `AC_FIELD_KEY`. Log: `"Found Acceptance Criteria field: {AC_FIELD_KEY} — ACs will be written to that field."`.
   - If not found, set `AC_FIELD_KEY = null`. Log: `"No Acceptance Criteria field detected — ACs will remain in the description."`.

2. A field whose name contains "story point" (case-insensitive) or whose key is exactly `story_points`. Common keys include `customfield_10016`, `customfield_10028`, `customfield_10037`, or `story_points`.
   - If found, store as `SP_FIELD_KEY`. Log: `"Found Story Points field: {SP_FIELD_KEY}"`.
   - If not found, set `SP_FIELD_KEY = null`. Log: `"No Story Points field detected — story point estimate will be written to description only."`.

If `FIELD_DISCOVERY_ISSUETYPE_ID` is null or the `getJiraIssueTypeMetaWithFields` call fails, set both `AC_FIELD_KEY = null` and `SP_FIELD_KEY = null` and continue.

Log all discoveries on one line before moving to Phase 3, e.g.:
> "AC field: customfield_10014 | SP field: customfield_10028 | Link type: Relates (id: 10003) | Priority scheme: custom (P1, P2, P3…)"

---

## Phase 3 — Fetch unresolved tickets

Build the JQL query based on `INCLUDE_EPICS`:

**When `INCLUDE_EPICS = false` (default):**
```
project = {PROJECT_KEY}
  AND statusCategory != Done
  AND resolution = Unresolved
  AND issuetype != Epic
  AND (labels NOT IN ("ai-fleshed-out") OR labels IS EMPTY)
ORDER BY created DESC
```

**When `INCLUDE_EPICS = true`:**
```
project = {PROJECT_KEY}
  AND statusCategory != Done
  AND resolution = Unresolved
  AND (labels NOT IN ("ai-fleshed-out") OR labels IS EMPTY)
ORDER BY created DESC
```

Run the query using `searchJiraIssuesUsingJql` with:
- `fields`: `summary`, `description`, `issuetype`, `priority`, `status`, `reporter`, `assignee`, `labels`, `components`
- `responseContentFormat: "markdown"`
- `maxResults: {MAX_TICKETS}`

If the total count exceeds `MAX_TICKETS`, tell the user:
> "Found X unresolved tickets — showing the newest {MAX_TICKETS}. Run again to continue with the next batch."

Store the full ordered list.

---

## Phase 4 — Parallel ticket dispatch

### Step 4.1 — Pre-dispatch confirmation

Display a table of all tickets about to be processed:

> "Ready to dispatch {N} parallel agents — one per ticket. Each agent will research, generate content, and write directly to Jira without further prompts."

| # | Ticket | Summary |
|---|--------|---------|
| 1 | PROJ-123 | {summary} |
| 2 | PROJ-124 | {summary} |
| … | … | … |

Then ask exactly:

> "Reply **YES** to dispatch all agents now, or **STOP** to cancel."

Wait for the user's reply.

- **STOP**: Print the final summary (Phase 6) with all tickets marked `⏹️ Session stopped before processing` and end.
- **YES**: Proceed to Step 4.2.

### Step 4.2 — Dispatch one agent per ticket (all in parallel)

Dispatch **all agents simultaneously** in a single message — one Agent call per ticket. Do not wait for one agent to finish before dispatching the next.

For each ticket, construct a self-contained agent prompt using the template below. The agent has no session context, so every value it needs must be present in the prompt.

---

**Agent prompt template** (fill in `{…}` with real values from the current session before dispatching):

```
You are fleshing out a single Jira ticket. Follow every instruction below exactly. Do not ask the user for input — write to Jira automatically after generating content.

## Session constants (do not re-fetch these)

- cloudId: {CLOUD_ID}
- site URL: {SITE_URL}
- AC_FIELD_KEY: {AC_FIELD_KEY or "null"}
- SP_FIELD_KEY: {SP_FIELD_KEY or "null"}
- RELATES_LINK_TYPE_ID: {RELATES_LINK_TYPE_ID or "null"}
- PRIORITY_NAME_MAP: {PRIORITY_NAME_MAP as JSON, e.g. {"P1":"P1","P2":"P2","P3":"P3","P4":"P4","P5":"P5"}}
- PRIORITY_FALLBACK_MAP: {PRIORITY_FALLBACK_MAP as JSON, e.g. {"P1":"Highest","P2":"High","P3":"Medium","P4":"Low","P5":"Lowest"}}

## Your assigned ticket

- Issue key: {ISSUE_KEY}
- Summary: {SUMMARY}
- Issue type: {ISSUETYPE}
- Priority: {PRIORITY}
- Status: {STATUS}
- Labels: {LABELS}
- Components: {COMPONENTS}
- Existing description:
{DESCRIPTION}

---

## Step A — Score for completeness

**Automatically skip** (do not write anything to Jira) if ALL three of the following are present in the existing description above:

1. A description of the problem or goal (at least 2 sentences or a bulleted list).
2. At least one line containing `given`, `when`, `then`, `AC:`, `acceptance criteria`, `definition of done`, or `done when` (case-insensitive).
3. At least one of: a verification step, a rollback step, or an error scenario.

If all three criteria are met, return exactly:
> RESULT: auto-skipped | {ISSUE_KEY} | Already complete

Then stop. Do not call any more tools.

---

## Step B — Research org context via Unblocked

**Step B.1 — URL extraction**
Scan the existing description for any URLs (GitHub, Confluence, Jira, Slack, runbooks). For each URL found, call `context_get_urls` with those URLs.

**Step B.2 — Topic research**
Call `context_research` with:
- `query`: the ticket summary plus 3–5 key noun phrases from the description (service names, technology names, error messages, AWS resource types, infra component names)
- `effort`: `medium`

If `context_research` errors or times out, note it and continue with ticket context only.

**Step B.3 — Extract org-specific facts**

From B.1 and B.2, extract:

| What to extract | Use in template |
|----------------|-----------------|
| Exact repository name(s) | Prerequisites: "You have write access to `{repo}`" |
| Slack channel(s) for the service or team | Error scenarios and rollback: "Post in `#{channel}`" |
| Runbook or doc URLs | Prerequisites, Implementation Notes, and References |
| Exact service or component names | Prerequisites, ACs, verification commands |
| Team or on-call owner | Rollback notification step |
| Related past incidents | Known Error Scenarios and References |
| Past PRs or fixes for similar problems | Implementation Notes and References |
| Environment-specific hostnames, namespaces, or cluster names | Verification commands |
| Any URL with a title or summary | References section |
| Jira ticket keys (e.g. `ENG-42`) in research or existing description | `RELATED_TICKET_KEYS` list (exclude {ISSUE_KEY} itself) |

**Step B.4 — Classify priority**

Use the ticket summary, description, issue type, labels, components, and the framework below to assign a priority.

| Priority | Jira Level | Assign when the ticket primarily… |
|----------|------------|-----------------------------------|
| P1 | Highest | Responds to an active incident; directly supports revenue generation; reduces Customer Service burden (training, automations, metrics tracking); provides dev training; is a flagged priority platform project |
| P2 | High | Is a run-the-business needful: routine maintenance, cost anomaly, compliance requirement, or an #ask-channel request |
| P3 | Medium | Improves reliability or resiliency: uptime improvements, failover capabilities, feature development |
| P4 | Low | Delivers a quality-of-life improvement with no direct business impact |
| P5 | Lowest | Does not clearly fit P1–P4 |

Steps:
1. Identify the dominant theme of the ticket.
2. Select the matching priority level from the table.
3. Write a 1–2 sentence rationale explaining the classification. Be specific: name the revenue flow, CS burden, or reliability concern that drove the decision.
4. Store: `PRIORITY_LEVEL` (e.g. `P1`), `PRIORITY_JIRA_NAME` = `PRIORITY_NAME_MAP[PRIORITY_LEVEL]` (the project-specific name discovered in Phase 2.5, e.g. `P2` or `High`), `PRIORITY_JIRA_FALLBACK` = `PRIORITY_FALLBACK_MAP[PRIORITY_LEVEL]` (the alternate name to try if the primary fails), `PRIORITY_RATIONALE` (your explanation).

---

## Step B.5 — Estimate story points

Using the ticket summary, description, Unblocked research, and the acceptance criteria you will generate, assign a story point estimate on the Fibonacci scale.

| Points | Assign when… |
|--------|-------------|
| 1 | Trivial change: single config value, copy edit, or rename. No logic change. Zero risk. |
| 2 | Small, well-understood change confined to one file or one endpoint. Minimal testing needed. |
| 3 | Moderate complexity: touches 1–2 services, standard pattern, low uncertainty. |
| 5 | Significant work: multiple services or layers, some design decisions, requires thorough testing. |
| 8 | Complex: cross-team dependencies, meaningful architectural impact, or high uncertainty requiring investigation. |
| 13 | Very complex: major cross-cutting change, multiple unknowns, likely needs a sub-spike or a breakdown. |
| 21 | Too large to estimate reliably — flag for breakdown in `STORY_POINTS_NOTE`. |

Steps:
1. Count the number of distinct acceptance criteria you will generate.
2. Identify how many services, repos, or infrastructure components are affected.
3. Assess uncertainty: are there open questions, `[OWNER TO CONFIRM]` placeholders, or missing Unblocked context?
4. Select the Fibonacci value that best fits.
5. Write a 1–2 sentence rationale explaining the estimate. Be specific.
6. Store: `STORY_POINTS` (the numeric value, e.g. `5`), `STORY_POINTS_RATIONALE` (your explanation), and `STORY_POINTS_NOTE` (any flag, e.g. `"Consider breaking this down"` for 21-point tickets, or empty string otherwise).

---

## Step C — Generate enriched content

Generate a full rewrite of the ticket description using the template below. Fill in real values from the ticket and Unblocked research. Use `[OWNER TO CONFIRM]` only for details neither the ticket nor Unblocked could answer.

**AC field behavior:**
- If AC_FIELD_KEY is set (not "null"): write the `## Acceptance Criteria` section content to that field and **omit** it from `description`.
- If AC_FIELD_KEY is "null": keep `## Acceptance Criteria` in `description`.

**Output template:**

---

## Summary

{1–2 sentence plain-English statement of what this ticket delivers and why it matters.}

---

## Priority

**{PRIORITY_LEVEL} — {PRIORITY_JIRA_NAME}**

{PRIORITY_RATIONALE}

---

## Story Points

**{STORY_POINTS}**

{STORY_POINTS_RATIONALE}{STORY_POINTS_NOTE — if non-empty, append on a new line: "⚠️ {STORY_POINTS_NOTE}"}

---

## Prerequisites

Before starting this ticket, verify each item below. A missing prerequisite is the most common reason tickets get stuck.

- [ ] {Specific access or permission required}
- [ ] {Specific tooling or environment requirement}
- [ ] {Any dependent ticket or migration that must be complete first}

If you are missing any prerequisite, stop and resolve it before proceeding.

---

## Acceptance Criteria

Each item below is a pass/fail test. The ticket is not done until every checkbox is checked.

### Functional Criteria

- [ ] Given {specific starting state}, when {specific user action or system event}, then {specific, observable, measurable outcome}.
- [ ] Given {specific starting state}, when {specific user action or system event}, then {specific, observable, measurable outcome}.
- [ ] {Any non-functional requirement expressed as a concrete, measurable number.}

### Out of Scope

- {Thing that sounds related but is excluded.}
- {[OWNER TO CONFIRM] — ask the reporter if this edge case is in or out.}

---

## How to Verify This Worked

Run each step in order after implementation.

**Step 1 — {What you are verifying}**
```
{exact command}
```
Expected output:
```
{exact expected output}
```

**Step 2 — {What you are verifying}**
```
{exact command or UI navigation path}
```
Expected result: {what success looks like}

---

## Known Error Scenarios

| Error / Symptom | Likely Cause | Exact Fix |
|-----------------|-------------|-----------|
| `{exact error message or symptom}` | {one-sentence cause} | {exact command or step} |
| `{exact error message or symptom}` | {one-sentence cause} | {exact command or step} |
| {[OWNER TO CONFIRM]} | Unknown | Ask {reporter or team} before unblocking yourself. |

If you hit an error not listed here, **do not push to production**. Post the exact error message in {[OWNER TO CONFIRM: Slack channel]} before proceeding.

---

## How to Roll Back

**Step 1 — {Rollback action}**
```
{exact rollback command}
```

**Step 2 — Verify the rollback succeeded**
```
{exact verification command}
```
Expected result: {what you should see}

**Step 3 — Notify the team**
Post in {[OWNER TO CONFIRM: Slack channel]}: "Rolled back {ISSUE_KEY} — {brief reason}."

---

## Implementation Notes

{Relevant technical context: architecture decisions, affected services, data model changes, API contract changes. Skip this section if there is nothing beyond what the ACs already state.}

---

## References

{List only URLs directly useful to an engineer working this ticket. Omit section if none found.}

- [{Link title or description}]({URL})

---

## Step D — Write to Jira

### Step D.1 — Write content

Call `editJiraIssue` with:
- `cloudId`: {CLOUD_ID}
- `issueIdOrKey`: {ISSUE_KEY}
- `contentFormat`: "markdown"
- `fields`:
  - If AC_FIELD_KEY is set (not "null") and SP_FIELD_KEY is set (not "null"):
    ```json
    {
      "description": "<all sections except Acceptance Criteria>",
      "{AC_FIELD_KEY}": "<Acceptance Criteria section content only, no header>",
      "{SP_FIELD_KEY}": {STORY_POINTS},
      "labels": ["ai-fleshed-out", ...existing labels from the ticket]
    }
    ```
  - If AC_FIELD_KEY is set (not "null") and SP_FIELD_KEY is "null":
    ```json
    {
      "description": "<all sections except Acceptance Criteria>",
      "{AC_FIELD_KEY}": "<Acceptance Criteria section content only, no header>",
      "labels": ["ai-fleshed-out", ...existing labels from the ticket]
    }
    ```
  - If AC_FIELD_KEY is "null" and SP_FIELD_KEY is set (not "null"):
    ```json
    {
      "description": "<full generated markdown>",
      "{SP_FIELD_KEY}": {STORY_POINTS},
      "labels": ["ai-fleshed-out", ...existing labels from the ticket]
    }
    ```
  - If both are "null":
    ```json
    {
      "description": "<full generated markdown>",
      "labels": ["ai-fleshed-out", ...existing labels from the ticket]
    }
    ```
  Preserve all existing labels. Do not add `ai-fleshed-out` twice.
  Note: `{SP_FIELD_KEY}` must be a JSON number (e.g. `5`), not a string.

Note the result (success or error message). Then **always** proceed to Step D.2 regardless of whether D.1 succeeded or failed — do not stop here.

### Step D.2 — Set priority (always runs, even if D.1 failed)

Call `editJiraIssue` with ONLY the priority field:
- `cloudId`: {CLOUD_ID}
- `issueIdOrKey`: {ISSUE_KEY}
- `fields`: `{"priority": {"name": "{PRIORITY_JIRA_NAME}"}}`

If D.2 fails (any error), immediately retry once with the fallback name:
- `fields`: `{"priority": {"name": "{PRIORITY_JIRA_FALLBACK}"}}`

If both attempts fail, log `"priority-unset"` and continue to Step E. Do not treat a priority-only failure as a full write failure — content may still have been written.

**After a successful D.2 when D.1 failed** — call `addCommentToJiraIssue` with:
- `cloudId`: {CLOUD_ID}
- `issueIdOrKey`: {ISSUE_KEY}
- `contentFormat`: "markdown"
- `comment`: the following markdown:
  ```
  **Priority set by jira-flesh-out:** {PRIORITY_LEVEL} — {PRIORITY_JIRA_NAME}

  {PRIORITY_RATIONALE}
  ```

This ensures the rationale is always persisted to the ticket. If the comment call fails, log it but do not change the result status.

**D.2 final status:**
- Both D.1 and D.2 failed → return: `RESULT: failed | {ISSUE_KEY} | {D.1 error}`
- D.1 failed, D.2 succeeded → return: `RESULT: priority-only | {ISSUE_KEY} | content write failed: {D.1 error}`
- D.1 succeeded, D.2 failed → return: `RESULT: written | {ISSUE_KEY} | priority-unset`
- Both succeeded → proceed to Step E.

## Step E — Link related tickets

Run only if RELATES_LINK_TYPE_ID is not "null" and RELATED_TICKET_KEYS is non-empty.

For each key in RELATED_TICKET_KEYS, call `createIssueLink` with:
- `cloudId`: {CLOUD_ID}
- `linkTypeId`: {RELATES_LINK_TYPE_ID}
- `inwardIssueKey`: {ISSUE_KEY}
- `outwardIssueKey`: {the related key}

409 Conflict = already linked, treat as success. 404 = skip that key. 403 = skip all linking for this ticket.

## Step F — Return result

Return exactly one of:
- `RESULT: written | {ISSUE_KEY} | linked: KEY1, KEY2`
- `RESULT: written | {ISSUE_KEY} | no related tickets`
- `RESULT: written | {ISSUE_KEY} | linking skipped (403)`
- `RESULT: written | {ISSUE_KEY} | priority-unset`
- `RESULT: priority-only | {ISSUE_KEY} | content write failed: {error}`
- `RESULT: failed | {ISSUE_KEY} | {error message}`
- `RESULT: auto-skipped | {ISSUE_KEY} | Already complete`
```

---

### Step 4.3 — Collect results

Wait for all agents to complete. Each agent returns a `RESULT:` line. Parse every result and build the Phase 6 summary table.

---

## Phase 5 — Generate enriched ticket content

For each ticket that needs fleshing out, generate a full rewrite of its description using the template below. Use the existing `summary`, `description`, `issuetype`, `labels`, and `components` as primary context, supplemented by the org-specific facts extracted from Unblocked in Step B.

**Priority order for filling in details:**
1. Facts from the ticket itself (summary, description, labels, components)
2. Facts retrieved from Unblocked (repo names, Slack channels, runbook URLs, service owners, related incidents)
3. `[OWNER TO CONFIRM]` — only when neither the ticket nor Unblocked provided an answer

**Formatting rules:**
- Use plain directive English. No jargon, no architectural abstractions.
- Every step must be a complete, self-contained instruction. Never say "configure X" without providing the exact command or file path.
- Every acceptance criterion must be independently testable. Avoid "the feature works correctly."
- Use real values from Unblocked wherever possible. Prefer a specific repo name, channel name, or hostname over a generic placeholder.
- Use `[OWNER TO CONFIRM]` only for details that neither the ticket nor Unblocked could answer.

**AC field behavior:**
- If `AC_FIELD_KEY` is set: write the `## Acceptance Criteria` section content to that field and **omit** the `## Acceptance Criteria` section from the description. The description will contain all other sections (Summary, Prerequisites, How to Verify, Known Error Scenarios, How to Roll Back, Implementation Notes, References).
- If `AC_FIELD_KEY` is null: keep the `## Acceptance Criteria` section in the description as usual.

---

### Priority classification

Before generating content, classify the ticket priority using this framework:

| Priority | Jira Level | Assign when the ticket primarily… |
|----------|------------|-----------------------------------|
| P1 | Highest | Responds to an active incident; directly supports revenue generation; reduces Customer Service burden (training, automations, metrics tracking); provides dev training; is a flagged priority platform project |
| P2 | High | Is a run-the-business needful: routine maintenance, cost anomaly, compliance requirement, or an #ask-channel request |
| P3 | Medium | Improves reliability or resiliency: uptime improvements, failover capabilities, feature development |
| P4 | Low | Delivers a quality-of-life improvement with no direct business impact |
| P5 | Lowest | Does not clearly fit P1–P4 |

Store the result as `PRIORITY_LEVEL`, `PRIORITY_JIRA_NAME` = `PRIORITY_NAME_MAP[PRIORITY_LEVEL]`, `PRIORITY_JIRA_FALLBACK` = `PRIORITY_FALLBACK_MAP[PRIORITY_LEVEL]`, and `PRIORITY_RATIONALE` before writing content. Always write priority in a separate `editJiraIssue` call (Step D.2) using `PRIORITY_JIRA_NAME`, with `PRIORITY_JIRA_FALLBACK` as the retry value if the first attempt fails.

### Output template (write this verbatim structure, filled in with real content)

```markdown
## Summary

{1–2 sentence plain-English statement of what this ticket delivers and why it matters. Suitable for someone who has never seen this system before.}

---

## Priority

**{PRIORITY_LEVEL} — {PRIORITY_JIRA_NAME}**

{PRIORITY_RATIONALE}

---

## Story Points

**{STORY_POINTS}**

{STORY_POINTS_RATIONALE}{STORY_POINTS_NOTE — if non-empty, append on a new line: "⚠️ {STORY_POINTS_NOTE}"}

---

## Prerequisites

Before starting this ticket, verify each item below. A missing prerequisite is the most common reason tickets get stuck.

- [ ] {Specific access or permission required, e.g. "You have write access to the `payments-service` repository in GitHub."}
- [ ] {Specific tooling or environment requirement, e.g. "You have run `make auth` and confirmed your session is valid."}
- [ ] {Any dependent ticket or migration that must be complete first, e.g. "PROJ-99 (Add DB column `users.verified_at`) is deployed to staging."}

If you are missing any prerequisite, stop and resolve it before proceeding. Continuing without prerequisites is the leading cause of broken deployments.

---

## Acceptance Criteria

Each item below is a pass/fail test. The ticket is not done until every checkbox is checked. If any item is ambiguous, ask the ticket reporter before writing code.

### Functional Criteria

- [ ] Given {specific starting state}, when {specific user action or system event}, then {specific, observable, measurable outcome}.
- [ ] Given {specific starting state}, when {specific user action or system event}, then {specific, observable, measurable outcome}.
- [ ] {Any non-functional requirement: performance threshold, error rate, latency cap — expressed as a concrete, measurable number.}

### Out of Scope

The following are explicitly NOT part of this ticket. Do not implement them.

- {Thing that sounds related but is excluded.}
- {[OWNER TO CONFIRM] — ask the reporter if this edge case is in or out.}

---

## How to Verify This Worked

Run each step in order after implementation. Do not skip steps — a later step may catch a failure that an earlier step missed.

**Step 1 — {What you are verifying}**
```
{exact command, e.g. curl -s https://staging.example.com/health | jq .}
```
Expected output:
```
{exact expected output or a description of the expected UI state}
```

**Step 2 — {What you are verifying}**
```
{exact command or UI navigation path}
```
Expected result: {what success looks like, stated specifically}

---

## Known Error Scenarios

If you encounter one of these errors, use the fix in the right column. Do not guess.

| Error / Symptom | Likely Cause | Exact Fix |
|-----------------|-------------|-----------|
| `{exact error message or observable symptom}` | {one-sentence cause} | {exact command or step to resolve it} |
| `{exact error message or observable symptom}` | {one-sentence cause} | {exact command or step to resolve it} |
| {[OWNER TO CONFIRM]} | Unknown | Ask {reporter or team} before unblocking yourself. |

If you hit an error not listed here, **do not push to production**. Post the exact error message in {[OWNER TO CONFIRM: Slack channel or incident channel]} before proceeding.

---

## How to Roll Back

If this change needs to be reverted after deployment, follow these steps in order. Rolling back out of order may cause data loss.

**Step 1 — {Rollback action}**
```
{exact rollback command}
```

**Step 2 — Verify the rollback succeeded**
```
{exact verification command}
```
Expected result: {what you should see when rollback is confirmed}

**Step 3 — Notify the team**
Post in {[OWNER TO CONFIRM: Slack channel]}: "Rolled back {ISSUE_KEY} — {brief reason}."

---

## Implementation Notes

{Relevant technical context for the developer: architecture decisions, affected services, data model changes, API contract changes. Keep this section brief. Implementation specifics that every developer should know before touching this code go here. Skip this section entirely if there is no useful technical context to add beyond what the ACs already state.}

---

## References

{List of relevant links found during research. Include only links that are directly useful to an engineer working this ticket. Omit this section entirely if no relevant URLs were found.}

- [{Link title or description}]({URL})
- [{Link title or description}]({URL})
```

---

## Phase 6 — Final summary

After the loop ends (all tickets processed, or user replied STOP), output a final results table:

| Ticket | Summary | Result |
|--------|---------|--------|
| PROJ-123 | Add login page | ✅ Written |
| PROJ-124 | Fix null pointer | ✅ Already complete — auto-skipped |
| PROJ-125 | Deploy config update | ⏭️ Skipped by user |
| PROJ-126 | Update config | ❌ Write failed: {error} |
| PROJ-127 | Add tests | ⏹️ Session stopped before processing |
| PROJ-128 | Fix query timeout | ⚠️ Written — priority-unset (both name attempts failed) |
| PROJ-129 | Resize cluster | ⚠️ Priority-only write succeeded; content write failed: {error} |

Then tell the user:

- How many tickets were written.
- How many were auto-skipped (already complete).
- How many were skipped by the user.
- How many failed, with the error for each.
- How many were not reached because the session was stopped early.
- If any written tickets contain `[OWNER TO CONFIRM]` placeholders: "These tickets have placeholders that need human input before they are developer-ready. Review them in Jira and fill in the bracketed sections."

---

## Error handling

| Situation | What to do |
|-----------|------------|
| Invalid or unknown project key | Say: "Project '{KEY}' was not found. Run `/jira-flesh-out` without an argument to see available projects." |
| Jira auth failure | Say: "Jira authentication failed. Reconnect Atlassian via the MCP settings dialog (`/mcp`) and try again." |
| `editJiraIssue` returns 403 Forbidden | Say: "You do not have permission to edit {ISSUE_KEY}. Ask a Jira admin to grant you Editor access on project {PROJECT_KEY}." |
| `editJiraIssue` returns 404 | Say: "Ticket {ISSUE_KEY} was not found or was deleted during processing. Skipping." |
| Zero unresolved tickets found | Say: "No unresolved tickets found in {PROJECT_KEY}. Nothing to do!" |
| All tickets already complete | Say: "All {N} open tickets in {PROJECT_KEY} already have complete acceptance criteria. Nothing to rewrite." |
| `context_research` returns an error or times out | Log "Unblocked unavailable — proceeding without org context" and continue generation using ticket fields only. Do not block on Unblocked failures. |
| `createIssueLink` returns 404 for a related ticket key | The related ticket no longer exists or is in a different site. Skip that key and continue linking the rest. |
| `createIssueLink` returns 403 | Insufficient permission to create links on `{ISSUE_KEY}`. Skip linking for this ticket entirely and note it in the summary line. |
