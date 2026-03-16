# Code Review Process

This document covers how we review code before it gets merged into the main branch. All team members should read through this at least once.

## Workflow

1. **Create a branch off main.** Name it something descriptive like `feature/upload-syllabus` or `fix/login-redirect` so the team knows what it's for. Use `git checkout -b feature/your-thing` to create it.

2. **Write code and commit as you go.** Use clear commit messages and avoid saving everything for one large commit at the end. Smaller commits are easier to review and easier to revert if something breaks.

3. **Push your branch and open a pull request against main.** The PR template will auto-fill when you create one. Fill out every section. Assign at least one teammate as a reviewer.

4. **Reviewer examines the code.** When reviewing, check for:
   - Does the code work? Pull the branch locally and test it if the change is significant.
   - Is it readable? Would someone else understand this in a few months?
   - Are there edge cases or unexpected inputs that could cause problems?
   - Are the files in the correct folders?
   - Are there any console errors or warnings?

   Leave comments directly on the lines that need changes. Be specific about what's wrong and suggest a fix.

5. **Developer addresses feedback.** Make the changes and push new commits to the same branch. The PR updates automatically.

6. **Approve and merge.** Once the reviewer is satisfied and CI is passing, they approve the PR. Use "Squash and merge" to keep the commit history clean, then delete the branch.

## Pull Request Size

Keep PRs between 100 and 500 lines of code. That's large enough to represent a meaningful change but small enough for a thorough review. If a PR goes past 500 lines, consider splitting it into smaller pieces.

## Rules

- No one pushes directly to main. All changes go through a pull request.
- Every PR needs at least one approval before merging.
- CI must pass. Both `backend-tests` and `frontend-tests` need to be green.
- You cannot approve your own PR. A different team member has to review it.

## Review Turnaround

Try to review PRs within 24 hours. If you're unavailable, let the team know in the group chat so someone else can pick it up.
