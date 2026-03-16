GradePilot – Autonomous Academic Planning Agent

Version 1.0  |  March 2026

### Overview
GradePilot is an autonomous academic planning agent built primarily in Python. Students upload course materials (syllabi, assignments, readings), and the system extracts tasks, prioritises them, generates personalised study plans, creates practice questions, and synchronises everything with Google Calendar.

This document summarises the architecture, DevOps tooling, and deployment pipeline used to build, test, and ship GradePilot.

### Local setup and running

- **Prerequisites**
  - **Python**: 3.11 or newer (3.12 recommended).
  - **Package manager**: `uv` or `pip` (examples below use `uv` first).
  - **Git**: to clone the repository.

- **Clone the repository**

```bash
git clone git@github.com:<your-org>/GradePilot.git
cd GradePilot
```

- **Create a virtual environment and install dependencies**

Using `uv` (preferred):

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Using `pip` directly (if you are not using `uv`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

- **Configuration**
  - All configuration is provided via environment variables (see **Configuration and Secrets** below).
  - At minimum, ensure any required API keys and database URLs are exported in your shell or stored in a local `.env` file loaded by your tooling.

- **Run the API locally**

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000` with the interactive docs at `http://127.0.0.1:8000/docs`.

- **Run tests and checks**

```bash
pytest
ruff check .
black . --check
mypy .
```

### Application Framework
- **Backend**: FastAPI on Python 3.12, used for all server-side logic, REST endpoints, and AI orchestration. FastAPI’s async support, OpenAPI generation, and Pydantic integration are core to the design.
- **AI Orchestration**: LangChain and LangGraph provide the orchestration layer between FastAPI and the model API.
  - **LangChain**: fixed pipelines for PDF ingestion, RAG over course materials, practice question generation, and task extraction.
  - **LangGraph**: stateful agent for adaptive re-scheduling (re-evaluating tasks, reprioritising, rescheduling, and updating Supabase and Google Calendar).
- **LLM Provider**: Google Gemini 1.5 Pro, configured once as the LangChain `ChatGoogleGenerativeAI` backend. Application code talks to LangChain/LangGraph, not directly to Gemini, so the model provider is swappable.
- **Database**: Supabase (PostgreSQL) for data storage and authentication.
  - Accessed only from the FastAPI backend (never directly from the frontend).
  - Supabase Python client for auth and file storage.
  - SQLAlchemy with the Supabase Postgres connection string for complex queries and LangChain vector store integration.
- **Frontend**: React + Vite single-page application for the student dashboard and admin views, served by the FastAPI backend.

### Build Toolchain
- **Dependency Management**: `uv` with `pyproject.toml` as the single source of truth and `uv.lock` for deterministic environments.
- **Linting & Formatting**: Ruff and Black run locally and in CI.
- **Type Checking**: mypy in strict mode across the codebase, including LLM output parsing and schema validation.
- **Testing**: pytest with:
  - `pytest-asyncio` for async FastAPI routes,
  - `pytest-mock` for isolating external APIs/LLM calls,
  - coverage enforcement at ≥80% line coverage (CI gate).
- **Containerisation**: Docker multi-stage build:
  - Builder stage installs dependencies and runs tests.
  - Production stage based on `python:3.12-slim`, copying only runtime artefacts to keep the image small.
- **Local Orchestration**: `docker-compose.yml` for FastAPI, a local Postgres (mirroring Supabase schema), and background workers.

### Configuration and Secrets
- Application configuration is provided via environment variables.
- Secrets (API keys, database credentials, OAuth credentials) are stored in platform-specific secret stores (GCP Secret Manager, GitHub Actions Secrets) and are never committed to the repository.

### Cloud Infrastructure
- **Platform**: Google Cloud Platform (GCP), aligned with Google Calendar and Gemini usage within a single GCP project.
- **Compute**: Cloud Run for containerised FastAPI deployment.
  - TLS termination and HTTPS handled by Cloud Run.
  - Auto-scaling with scale-to-zero in non-production; minimum instances set to 1 in production to reduce cold starts.
  - Deployments performed with `gcloud run deploy` against tagged container images.

### CI/CD Pipeline
- **Platform**: GitHub Actions.
- **Workflows**:
  - `ci.yml` runs on every push and pull request.
  - `deploy.yml` runs on pushes to `main` only.
- **Pipeline Stages**:
  - Lint + type check (Ruff, Black, mypy).
  - Tests + coverage (`pytest`, coverage ≥80%).
  - Build and push Docker image.
  - Deploy to Cloud Run for the `main` branch.
- **Branch Policy**:
  - Feature branches follow `feature/<story-id>-short-description`.
  - Pull requests to `main` require at least one review and a green CI pipeline.
  - Direct pushes to `main` are disabled; deployments are triggered only from `main`.
- **Secrets in CI**:
  - Stored as GitHub Actions Secrets and injected as environment variables.
  - Never hard-coded in workflows or logged.

