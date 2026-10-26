# Job Portal Applications Agent

> Live docs (README rendered): **https://agent-job-applications.fly.dev/**

Autonomous UK tech contract & permanent job-application pipeline for Rifat Erdem Sahin — search, rank, dedupe, queue, and track applications across UK job portals, led by **JobServe UK**.

Operational rules live in [`specs/hermes-spec.yaml`](specs/hermes-spec.yaml) (the living Hermes specification). The agent's soul and memory are mirrored in [`soul/`](soul/).

## Repository layout

| Path | Purpose |
|---|---|
| `specs/hermes-spec.yaml` | Living operational spec: profile, clearance, priority heuristics, platforms, logging |
| `scripts/apply_jobserve.py` | JobServe runner: WebForms POST search → mobile-results parse → rank → dedupe → queue |
| `templates/cv_mappings.json` | Job-description → CV routing rules (CVLauncher artifacts) |
| `metadata/run_history.json` | Run telemetry + cross-run application-ID deduplication |
| `metadata/queues/` | Dated, ranked application queues (generated output) |
| `assets/cvs/` | CV variants referenced by the routing matrix |
| `soul/` | Agent SOUL.md + MEMORY.md + USER.md (soul memory) |

## Usage

```bash
# search, rank (clearance > geography > IR35 > domain), dedupe, write queue
python3 scripts/apply_jobserve.py search --keywords "AI Engineer" --location "Cambridge" --limit 15

# record a submission completed in the browser session
python3 scripts/apply_jobserve.py mark-applied --id <JOB_ID> --cv cv_ai_engineer.pdf

# run summary
python3 scripts/apply_jobserve.py stats
```

## Decision engine (summary)

1. **Clearance (Tier 0)** — NATO / SC / DV-cleared roles first
2. **Geography** — Cambridge (25 mi) → London/Hybrid → UK Remote → EU Remote
3. **Tax status** — Outside IR35 first; umbrella/PAYE-only excluded
4. **Domain** — AI/GenAI → SRE → DevOps/DevSecOps → Architect → Platform/Data

Exclusions: third-party ATS walls, hard redirect blockers, duplicate application IDs (strict skip across runs).

Human execution protocol: 3–6 minutes between submissions, humanised pacing, and **immediate human handover on any captcha** (spec section 6).

## Deployment

Static docs site on Fly.io (`fly.toml`, nginx) — serves this README rendered at the app root.

⚠️ This repository is public: credential **values** never live here — only secret *names* and their vault (`dp-kv-deliverypilot`).
