## Workflow and Team Progress

This document covers how we plan, estimate, track, and coordinate work for GradePilot. 

## Tools

- **Issue tracking system**: GitHub Issues
- **Progress tracking**: GitHub Projects (Kanban board)
- **Communication channel**: Discord

## Workflow

We track all work using the same board columns:

Backlog → In Progress → Review → Done

1. **Create a GitHub Issue for every piece of work.** Each issue must include:
   - A clear summary
   - Acceptance criteria (checkboxes)
   - Story points (1–4)

2. **Backlog.** The issue is defined and estimated, and ready to be picked up.

3. **In Progress.** The issue has an owner and active work (branch/PR in progress).

4. **Review.** The issue has a PR open and is waiting for review/changes/CI.

5. **Done.** The PR is merged to `main` and acceptance criteria are met.

## Estimation (GradePilot story points)

We estimate work using story points: **1, 2, 3, 4**. These points are based on **scope and risk** for GradePilot’s stack (FastAPI, React, AI pipelines, Supabase, Google Calendar), not exact hours.

- **1 point (tiny, low risk)**: a single small change in one area  
  - e.g., small UI tweak (one component)  
  - e.g., minor FastAPI route change (add/rename one response field)  
  - e.g., update a single doc, test, or config with no new behavior

- **2 points (small, contained)**: one clear deliverable with minimal dependencies  
  - e.g., add one simple API endpoint (request/response + basic validation)  
  - e.g., add one frontend page/view that calls an existing endpoint  
  - e.g., add tests for one endpoint or one pipeline step

- **3 points (medium, multi-part)**: touches multiple files/modules or introduces meaningful integration work  
  - e.g., syllabus upload flow (API + validation + storage wiring + tests)  
  - e.g., tasks dashboard view (multiple API calls + loading/error states + tests)  
  - e.g., add a new LangChain pipeline step plus schema/parsing + tests

- **4 points (large/high risk)**: spans multiple components (backend + frontend + integrations) or has major unknowns  
  - e.g., end-to-end “generate study plan” slice (ingestion/RAG + API + UI + tests)  
  - e.g., new Google Calendar integration (OAuth + sync logic + failure handling)  
  - e.g., new Supabase schema + auth rules + API changes + UI updates  
  - **Rule**: if it’s a 4, try to split into 2–3 point issues before starting.

## Communication 

Discord is the default place for team coordination.

## Meetings

- **Weekly planning (30–45 min)**: prioritize, estimate, and assign owners.
- **Mid-week check-in (10–15 min)**: unblock work and rebalance if needed.
- **Weekly demo/review (20–30 min)**: show completed work, close issues, capture follow-ups.

## User stories completed

Ensure user stories align with project goals, are well-defined, and consistently delivered.

- **How we measure**: count stories moved to **Done** (merged + acceptance criteria met)
- **What we expect**: consistent throughput and fewer carry-overs
- **Action if low**: tighten acceptance criteria, split large stories, and remove blockers earlier

## Amount of unplanned work

Identify and analyze unplanned tasks to improve iteration planning and minimize disruptions.

- **How we measure**: label issues created mid-iteration as `unplanned` and track count/points
- **What we expect**: unplanned work stays within an agreed buffer
- **Action if high**: add capacity buffer, improve discovery/specs, and address root causes (bugs, missing dependencies, scope creep)

