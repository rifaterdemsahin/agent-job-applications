```yaml
version: "2.1"
agent_name: "Job Portal Applications Agent"
target_user: "Rifat Erdem Sahin"
primary_domain: "UK Tech Contract & Permanent Recruitment Automation"
last_updated: "2026-10-26"

# ==============================================================================
# 1. CORE IDENTITY & CREDENTIAL PROFILE
# ==============================================================================
profile:
  candidate_name: "Rifat Erdem Sahin"
  primary_contact_email: "info@pexabo.com"
  registration_email: "info@pexabo.com"
  location_base: "Cambridge & London, United Kingdom"
  right_to_work: "UK Citizen"
  availability: "Immediate"
  target_day_rate:
    range_gbp: "£400 - £1,500/day"
    default_strategy: "Match advertised role band; fallback £550-£750/day"

clearance_profile:
  held_clearance: "NATO Secret"
  imminent_clearance: "SC Clearance (treat as SC-eligible / imminent)"
  clearable_status: "DV Clearable / BPSS compliant"

credential_vault:
  platform: "Azure Key Vault"
  vault_name: "dp-kv-deliverypilot"
  account: "info@deliverypilot.net"
  stored_secrets:
    - "jobserve-login-username"
    - "jobserve-login-password"
    - "apply-profile-metadata"

# ==============================================================================
# 2. SOURCE CODE, WORKFLOW ENGINE & METADATA REPOSITORY
# ==============================================================================
code_repository:
  url: "https://github.com/rifaterdemsahin/agent-job-applications"
  branch: "main"
  sync_policy: "Persist all automation scripts, configuration specs, run orchestrators, and execution metadata."
  tracked_artifacts:
    - path: "specs/hermes-spec.yaml"
      description: "Living Hermes operational specification and priority heuristics."
    - path: "scripts/apply_jobserve.py"
      description: "Headless/browser automation runner with humanized delays and form population."
    - path: "metadata/run_history.json"
      description: "Execution run metadata, telemetry, timestamp logs, and deduplication IDs."
    - path: "templates/cv_mappings.json"
      description: "Rule mappings matching job descriptions to CVLauncher artifacts."

# ==============================================================================
# 3. TARGET PLATFORMS & INPUT CHANNELS
# ==============================================================================
platforms:
  primary:
    - name: "JobServe UK"
      url: "https://www.jobserve.com/gb/en/"
      status: "Active / Signed In"
  secondary_expansion:
    - "CWJobs"
    - "Totaljobs"
    - "Reed.co.uk"
    - "CV-Library"
    - "Wellfound (AngelList Talent)"
    - "Security Cleared Jobs UK"
  inbox_alert_crawlers:
    gmail_label: "1_borrow_followup"
    triggers:
      - "JobServe Job Suggestion"
      - "Wellfound Job Alerts"

# ==============================================================================
# 4. CV & ASSET ROUTING MATRIX (CVLauncher)
# ==============================================================================
cv_launcher_matrix:
  base_project: "CVLauncher & LinkedIn CV Repository"
  routing_rules:
    - role_cluster: ["AI Engineer", "GenAI", "Agentic AI", "Prompt Engineer", "LLM Systems"]
      cv_file: "cv_ai_engineer.pdf"
    - role_cluster: ["Site Reliability Engineer", "SRE", "DevOps Engineer", "Cloud Infrastructure"]
      cv_file: "cv_sre.pdf" / "cv_devops.pdf"
    - role_cluster: ["Platform Engineer", "Lead Platform Engineer", "Data Platform"]
      cv_file: "cv_platform_engineer.pdf"
    - role_cluster: ["Software Architect", "AI Architect", "Enterprise Architect", "Solutions Architect"]
      cv_file: "cv_solutions_architect.pdf" / "cv_ai_architect.pdf"
    - role_cluster: ["Product Manager", "Platform Product Manager"]
      cv_file: "cv_product_manager.pdf"

# ==============================================================================
# 5. DECISION ENGINE: SELECTION & FILTER HIERARCHY
# ==============================================================================
hierarchy_pipeline:
  step_1_clearance_priority:
    weight: HIGHEST (Tier 0)
    rule: "Prioritize NATO / SC / DV Clearable roles ahead of non-cleared roles."
  
  step_2_geographic_priority:
    1: "Cambridge (within 25 miles)"
    2: "London / Hybrid"
    3: "UK Remote"
    4: "EU Remote"

  step_3_tax_status_priority:
    1: "Outside IR35 (Always apply first)"
    2: "Inside IR35 (Apply when Outside IR35 pool is depleted or role is an exceptional AI/SRE/Architect fit)"
    exclude: ["Umbrella/PAYE-only without agency day rate option"]

  step_4_role_domain_order:
    1: "AI / GenAI / Agentic AI / ML Engineering"
    2: "Site Reliability Engineering (SRE)"
    3: "DevOps / DevSecOps"
    4: "Software / Solutions / Enterprise Architect"
    5: "Platform Engineering / Data Lead"

exclusion_filters:
  - "External third-party ATS walls requiring separate complex manual logins (e.g. emagine) unless credentials exist"
  - "Third-party redirect walls with hard blockers (e.g. Jobg8 walls)"
  - "Duplicate Application IDs (strict skip of previously submitted IDs across runs)"

# ==============================================================================
# 6. EXECUTION & ANTI-DETECTION RUNTIME (Human Simulation)
# ==============================================================================
human_execution_protocol:
  interval_delay: "3 to 6 minutes between consecutive form submissions"
  in_page_actions:
    - "Scroll page naturally to read full advert description before clicking apply"
    - "Simulate human keystroke pauses when filling cover notes and fields"
  captcha_mitigation:
    on_trigger: "Verify Human / reCAPTCHA"
    action: "IMMEDIATELY halt automated clicks; pause pipeline; hand control over to human operator for clearance"
    resume_hook: "Verify login session active; resume paced batch execution"

# ==============================================================================
# 7. LOGGING, SPEC REFRESH & GOOGLE DRIVE INTEGRATION
# ==============================================================================
storage_and_reporting:
  specs_folder_url: "https://drive.google.com/drive/folders/1V_No6VCg3fmdKQgwTwTjYa_QeCjlOai9"
  specs_doc_title: "Job Portal Applications — Specs (updated)"
  specs_update_policy: "Sync and rewrite specification doc whenever apply rules, credentials, or target lists evolve."
  
  daily_application_log:
    folder_naming: "JobServe Applications -> YYYY-MM-DD"
    output_formats:
      - format: "Google Doc Daily Summary"
        naming: "JobServe Applications Log YYYY-MM-DD — <batch_type>"
      - format: "Google Sheet Application Tracker"
        schema_columns:
          - "Timestamp"
          - "Job Portal / Source"
          - "Job ID / Reference"
          - "Job Title"
          - "Company / Agency"
          - "Location"
          - "Day Rate / Salary"
          - "IR35 Status"
          - "Clearance Level"
          - "CV Used"
          - "Submission Status"

```

---

### Key Updates Applied

* **Primary Contact Email:** Standardized to `info@pexabo.com` across profile settings and submission field injectors.
* **Code & Metadata Store:** Linked [`github.com/rifaterdemsahin/agent-job-applications`](https://github.com/rifaterdemsahin/agent-job-applications) under section 2 (`code_repository`) to track all automation scripts, runner metadata, CV routing rules, and Hermes spec updates alongside the Google Drive logs.
