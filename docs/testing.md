# GradePilot Testing Guide

## Purpose
This document explains the testing setup for GradePilot and how the team should write and run tests during the semester.

## Testing Goals
The testing system should help the team:

- catch bugs early
- verify that code changes do not break existing features
- support pull request review with automated checks
- track test coverage over time

## Selected Testing Tools
Because GradePilot is planned as a Next.js frontend with a Python FastAPI backend, the recommended testing stack is:

### Frontend
- Jest
- React Testing Library

### Backend
- pytest
- pytest-cov

### Continuous Integration
- GitHub Actions

## Test Organization
Tests should live inside the same overall project repository, but they should not be part of the production deployment.

### Planned Testing Stack
- Frontend: Jest + React Testing Library
- Backend: pytest + pytest-cov
- CI: GitHub Actions

### Documentation
See `docs/testing.md` for the testing process, conventions, and commands.
```text
frontend/
  __tests__/

backend/
  tests/
