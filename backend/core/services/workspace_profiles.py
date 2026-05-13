"""Static tenant-scoped workspace profiles for vertical Playground and GPC handoff."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from db.models import Workspace

SUPPORTED_INDUSTRIES = {
    "banking_fintech",
    "healthcare_hospital",
    "insurance",
    "legal_compliance",
    "government_public_sector",
    "enterprise_operations",
    "generic",
}
REGULATED_INDUSTRIES = {
    "banking_fintech",
    "healthcare_hospital",
    "insurance",
    "legal_compliance",
    "government_public_sector",
}


def _scenario(
    scenario_id: str,
    title: str,
    prompt: str,
    workflow: list[str],
    models_tools: list[str],
    evidence_emphasis: list[str],
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "title": title,
        "prompt": prompt,
        "suggested_workflow": workflow,
        "suggested_models_tools": models_tools,
        "evidence_emphasis": evidence_emphasis,
    }


PROFILE_TEMPLATES: dict[str, dict[str, Any]] = {
    "generic": {
        "profile_name": "Generic Sovereign AI Workspace",
        "risk_tier": "generic",
        "policy_pack": "generic_foundation_v1",
        "policy_checks": [
            "Require approved model route before execution.",
            "Capture the workflow objective before pipeline packaging.",
            "Flag unsupported public claims for review.",
        ],
        "evidence_requirements": [
            "workflow objective",
            "policy decision",
            "model and tool used",
            "cost trace",
            "audit export",
        ],
        "restricted_actions": [
            "No public compliance claims without founder review.",
        ],
        "recommended_model_tool_constraints": [
            "Prefer workspace-approved local or BYOS routes.",
            "Restrict external fallback unless policy explicitly permits it.",
        ],
        "default_blocking_rules": [
            "Block unsupported compliance or regulatory claims.",
            "Escalate high-risk actions for human review.",
        ],
        "gpc_templates": [
            "Objective -> workflow -> policy -> evidence -> cost -> deployment",
        ],
        "sample_workflows": [
            "Support triage with budget and evidence controls",
            "Internal policy assistant with approval gate",
        ],
        "suggested_demo_prompts": [
            "We want to use AI to triage support tickets without leaking sensitive data.",
            "Help us design a governed internal policy assistant.",
        ],
        "default_demo_scenarios": [
            _scenario(
                "generic_support_triage",
                "Support ticket triage",
                "We want to use AI to triage support tickets, summarize the case, route it to the right team, and keep an audit trail.",
                [
                    "Read inbound ticket",
                    "Classify urgency and sensitive content",
                    "Summarize the case",
                    "Route to the correct team",
                    "Write replayable evidence",
                ],
                ["approved_chat_model", "ticket_router", "audit_archive"],
                ["approval trail", "policy decision", "cost trace", "audit export"],
            ),
            _scenario(
                "generic_policy_assistant",
                "Internal policy assistant",
                "We want an AI assistant that answers internal policy questions using approved sources only.",
                [
                    "Retrieve approved sources",
                    "Answer with citations",
                    "Escalate uncertain cases",
                    "Store evidence and replay context",
                ],
                ["approved_retrieval_model", "policy_index", "evidence_export"],
                ["source references", "human review", "audit export", "versioned artifact"],
            ),
        ],
    },
    "banking_fintech": {
        "profile_name": "Banking / Fintech Controlled Workspace",
        "risk_tier": "regulated",
        "policy_pack": "banking_fintech_guardrails_v1",
        "policy_checks": [
            "No external fallback unless the tenant policy pack allows it.",
            "Require approved model and tool registry matches.",
            "Force human review for high-risk routing or decisions.",
        ],
        "evidence_requirements": [
            "approval trail",
            "policy decision",
            "model/tool used",
            "audit export",
            "cost trace",
        ],
        "restricted_actions": [
            "No unsupported credit, fraud, or compliance claims.",
            "No external tool fallback by default.",
        ],
        "recommended_model_tool_constraints": [
            "Use approved private runtime or single-node vLLM route.",
            "Restrict output to workflow assist, not autonomous final decisions.",
        ],
        "default_blocking_rules": [
            "Block direct customer-impacting decisions without review.",
            "Require evidence capture and replay on all regulated scenarios.",
        ],
        "gpc_templates": [
            "Banking triage -> policy review -> human approval -> replay archive",
        ],
        "sample_workflows": [
            "Suspicious transaction escalation",
            "Loan memo review with policy checkpoints",
        ],
        "suggested_demo_prompts": [
            "We want AI to triage suspicious transactions and route high-risk cases for approval.",
        ],
        "default_demo_scenarios": [
            _scenario(
                "banking_loan_memo_review",
                "Loan memo review",
                "Review a loan memo, identify risk flags, summarize missing evidence, and route it for approval.",
                ["Read memo", "Flag risk signals", "Summarize findings", "Route for review", "Archive decision trace"],
                ["approved_chat_model", "loan_policy_lookup", "audit_archive"],
                ["approval trail", "policy decision", "model/tool used", "audit export", "cost trace"],
            ),
            _scenario(
                "banking_suspicious_transaction_triage",
                "Suspicious transaction triage",
                "Triage suspicious transactions, explain risk basis, and route urgent cases without external fallback.",
                ["Read transaction event", "Assess risk pattern", "Escalate urgent cases", "Record replay evidence"],
                ["approved_chat_model", "transaction_rule_engine", "replay_archive"],
                ["claim decision trace", "human approval", "cost trace", "replay record"],
            ),
            _scenario(
                "banking_complaint_escalation",
                "Complaint escalation",
                "Summarize customer complaints, detect regulatory themes, and route them to the right queue.",
                ["Read complaint", "Detect regulatory theme", "Summarize case", "Route to team", "Store evidence"],
                ["approved_chat_model", "queue_router", "audit_export"],
                ["approval trail", "policy basis", "audit export", "cost trace"],
            ),
            _scenario(
                "banking_policy_qa",
                "Internal policy Q&A",
                "Answer internal policy questions using approved banking policy sources only.",
                ["Retrieve policy sources", "Answer with basis", "Escalate uncertainty", "Store evidence"],
                ["approved_retrieval_model", "policy_index", "evidence_export"],
                ["source references", "policy decision", "audit export", "versioned artifact"],
            ),
        ],
    },
    "healthcare_hospital": {
        "profile_name": "Healthcare / Hospital Controlled Workspace",
        "risk_tier": "regulated",
        "policy_pack": "healthcare_phi_guardrails_v1",
        "policy_checks": [
            "No external fallback unless tenant policy permits it.",
            "Require human review for high-risk patient-facing outputs.",
            "Enforce PHI handling warnings and replay capture.",
        ],
        "evidence_requirements": [
            "PHI handling",
            "redaction",
            "human review",
            "restricted fallback",
            "audit log",
        ],
        "restricted_actions": [
            "No autonomous patient-impacting decisions.",
            "No compliance claim language without approval.",
        ],
        "recommended_model_tool_constraints": [
            "Use private runtime or single-node vLLM behind BYOS gateway.",
            "Prefer redaction-aware workflows with human approval gates.",
        ],
        "default_blocking_rules": [
            "Block unreviewed high-risk patient-facing output.",
            "Require audit/replay and evidence capture on all PHI-bearing flows.",
        ],
        "gpc_templates": [
            "PHI-safe intake -> redaction -> review -> replay archive",
        ],
        "sample_workflows": [
            "Incident report triage",
            "Patient intake summary with redaction check",
        ],
        "suggested_demo_prompts": [
            "We want to summarize patient intake while redacting PHI and requiring human review.",
        ],
        "default_demo_scenarios": [
            _scenario(
                "healthcare_patient_intake_summary",
                "Patient intake summary",
                "Summarize patient intake, flag risk indicators, redact PHI where needed, and route for review.",
                ["Read intake", "Detect PHI", "Summarize clinically", "Route for review", "Archive evidence"],
                ["approved_chat_model", "phi_redaction_check", "audit_archive"],
                ["PHI handling", "redaction", "human review", "audit log"],
            ),
            _scenario(
                "healthcare_phi_redaction_check",
                "PHI redaction check",
                "Evaluate whether a draft response leaks PHI and produce a safer fallback.",
                ["Scan response", "Detect PHI risk", "Propose redacted draft", "Store audit evidence"],
                ["approved_chat_model", "redaction_guard", "evidence_export"],
                ["PHI handling", "redaction", "restricted fallback", "audit log"],
            ),
            _scenario(
                "healthcare_incident_report_triage",
                "Incident report triage",
                "Triage incident reports, detect safety/compliance issues, and escalate urgent cases.",
                ["Read report", "Assess severity", "Escalate urgent issues", "Create replay record"],
                ["approved_chat_model", "incident_router", "replay_archive"],
                ["human review", "restricted fallback", "audit log", "replay record"],
            ),
            _scenario(
                "healthcare_discharge_instruction_draft",
                "Discharge instruction draft",
                "Draft discharge instructions for staff review without making unapproved medical claims.",
                ["Read case summary", "Draft instructions", "Require human review", "Archive approved version"],
                ["approved_chat_model", "staff_review_queue", "versioned_archive"],
                ["human review", "restricted fallback", "audit log", "versioned artifact"],
            ),
        ],
    },
    "insurance": {
        "profile_name": "Insurance Controlled Workspace",
        "risk_tier": "regulated",
        "policy_pack": "insurance_claims_guardrails_v1",
        "policy_checks": [
            "Require human approval on claim-impacting outputs.",
            "No external fallback unless explicitly approved.",
            "Capture decision basis and replay evidence.",
        ],
        "evidence_requirements": [
            "claim decision trace",
            "human approval",
            "policy basis",
            "cost/routing control",
            "replay record",
        ],
        "restricted_actions": [
            "No autonomous claim denials or approvals.",
        ],
        "recommended_model_tool_constraints": [
            "Constrain to claim support workflows and approved policy tools.",
        ],
        "default_blocking_rules": [
            "Block final claim decisions without human approval.",
            "Require replay and cost trace on all claim workflows.",
        ],
        "gpc_templates": [
            "Claims triage -> policy basis -> approval -> replay archive",
        ],
        "sample_workflows": [
            "Claims intake triage",
            "Fraud signal escalation",
        ],
        "suggested_demo_prompts": [
            "We want AI to triage claims and flag fraud risk without making final claim decisions.",
        ],
        "default_demo_scenarios": [
            _scenario(
                "insurance_claims_intake_triage",
                "Claims intake triage",
                "Summarize a claim, identify urgency and missing evidence, and route to the right adjuster queue.",
                ["Read claim", "Assess urgency", "Summarize case", "Route to adjuster", "Store replay evidence"],
                ["approved_chat_model", "claims_router", "replay_archive"],
                ["claim decision trace", "human approval", "policy basis", "replay record"],
            ),
            _scenario(
                "insurance_coverage_question_summary",
                "Coverage question summary",
                "Answer internal coverage questions with policy basis and escalation for uncertain cases.",
                ["Retrieve policy basis", "Summarize coverage", "Escalate uncertainty", "Archive evidence"],
                ["approved_retrieval_model", "coverage_policy_index", "audit_export"],
                ["policy basis", "human approval", "replay record", "cost/routing control"],
            ),
            _scenario(
                "insurance_fraud_signal_flagging",
                "Fraud signal flagging",
                "Flag potential fraud signals and route them to investigation without making final determinations.",
                ["Read claim signals", "Flag anomalies", "Route to investigation", "Create replay record"],
                ["approved_chat_model", "fraud_rules", "replay_archive"],
                ["claim decision trace", "human approval", "replay record", "cost/routing control"],
            ),
            _scenario(
                "insurance_adjuster_workflow_assist",
                "Adjuster workflow assist",
                "Help adjusters summarize case files and gather missing documents under policy controls.",
                ["Read file", "Summarize case", "List missing docs", "Archive audit trail"],
                ["approved_chat_model", "document_checklist_tool", "audit_export"],
                ["policy basis", "human approval", "audit export", "cost/routing control"],
            ),
        ],
    },
    "legal_compliance": {
        "profile_name": "Legal / Compliance Controlled Workspace",
        "risk_tier": "regulated",
        "policy_pack": "legal_compliance_guardrails_v1",
        "policy_checks": [
            "Require source references for policy and contract outputs.",
            "Escalate sensitive matters for human approval.",
            "No public legal or compliance claim language without review.",
        ],
        "evidence_requirements": [
            "source references",
            "human approval",
            "sensitivity controls",
            "versioned artifact",
        ],
        "restricted_actions": [
            "No unreviewed legal conclusions.",
        ],
        "recommended_model_tool_constraints": [
            "Use retrieval-anchored responses with approved internal sources only.",
        ],
        "default_blocking_rules": [
            "Block unsupported legal or compliance claims.",
            "Require versioned artifacts and human review for sensitive outputs.",
        ],
        "gpc_templates": [
            "Legal review -> source basis -> approval -> versioned artifact",
        ],
        "sample_workflows": [
            "Contract clause review",
            "Policy exception routing",
        ],
        "suggested_demo_prompts": [
            "We want AI to review contracts, surface risky clauses, and require human approval before any action.",
        ],
        "default_demo_scenarios": [
            _scenario(
                "legal_contract_clause_review",
                "Contract clause review",
                "Review contract clauses, identify risk, and attach source-backed reasoning for counsel review.",
                ["Read clause", "Assess risk", "Attach source basis", "Route for counsel review"],
                ["approved_retrieval_model", "contract_clause_index", "versioned_archive"],
                ["source references", "human approval", "sensitivity controls", "versioned artifact"],
            ),
            _scenario(
                "legal_redline_summary",
                "Redline summary",
                "Summarize redlines between versions and flag material changes for human review.",
                ["Compare versions", "Summarize changes", "Flag material issues", "Archive versioned artifact"],
                ["approved_chat_model", "document_diff_tool", "versioned_archive"],
                ["source references", "human approval", "versioned artifact", "sensitivity controls"],
            ),
            _scenario(
                "legal_compliance_memo_draft",
                "Compliance memo draft",
                "Draft a compliance memo using approved sources and mark anything requiring counsel review.",
                ["Retrieve sources", "Draft memo", "Mark review points", "Archive versioned memo"],
                ["approved_retrieval_model", "policy_index", "versioned_archive"],
                ["source references", "human approval", "versioned artifact", "sensitivity controls"],
            ),
            _scenario(
                "legal_policy_exception_routing",
                "Policy exception routing",
                "Identify policy exceptions and route them to the correct approver with evidence attached.",
                ["Read request", "Map policy exception", "Route approver", "Archive evidence"],
                ["approved_chat_model", "policy_index", "audit_export"],
                ["source references", "human approval", "sensitivity controls", "audit export"],
            ),
        ],
    },
    "government_public_sector": {
        "profile_name": "Government / Public Sector Controlled Workspace",
        "risk_tier": "regulated",
        "policy_pack": "government_public_sector_guardrails_v1",
        "policy_checks": [
            "Restrict external fallback by default.",
            "Require sensitive-record handling warnings.",
            "Force review on high-risk public-sector decisions.",
        ],
        "evidence_requirements": [
            "approval trail",
            "policy decision",
            "audit export",
            "replay record",
        ],
        "restricted_actions": [
            "No public compliance or mission claims without approval.",
        ],
        "recommended_model_tool_constraints": [
            "Use approved tenant-scoped runtime and records-safe tooling.",
        ],
        "default_blocking_rules": [
            "Block high-risk outputs without review.",
            "Require audit/replay on all sensitive-record flows.",
        ],
        "gpc_templates": [
            "Public-sector triage -> sensitivity screen -> approval -> replay archive",
        ],
        "sample_workflows": [
            "Records sensitivity screening",
            "Case intake triage",
        ],
        "suggested_demo_prompts": [
            "We want AI to triage public-sector intake and screen sensitive records with approval gates.",
        ],
        "default_demo_scenarios": [
            _scenario(
                "government_case_intake_triage",
                "Case intake triage",
                "Triage case intake, classify urgency, and route it under tenant policy controls.",
                ["Read intake", "Classify urgency", "Route to team", "Store replay evidence"],
                ["approved_chat_model", "case_router", "replay_archive"],
                ["approval trail", "policy decision", "audit export", "replay record"],
            ),
            _scenario(
                "government_records_sensitivity_screening",
                "Records sensitivity screening",
                "Screen records for sensitivity and enforce restrictions before drafting any summary.",
                ["Read record", "Assess sensitivity", "Apply restrictions", "Archive evidence"],
                ["approved_chat_model", "record_sensitivity_tool", "audit_export"],
                ["approval trail", "policy decision", "audit export", "replay record"],
            ),
            _scenario(
                "government_procurement_exception_summary",
                "Procurement exception summary",
                "Summarize a procurement exception request and route it to the correct review path.",
                ["Read request", "Map exception path", "Summarize rationale", "Archive review trail"],
                ["approved_chat_model", "policy_index", "audit_export"],
                ["approval trail", "policy decision", "audit export", "replay record"],
            ),
            _scenario(
                "government_public_service_routing_assist",
                "Public-service routing assist",
                "Route inbound service requests to the correct team with evidence and budget controls.",
                ["Read request", "Classify service need", "Route to team", "Store replay evidence"],
                ["approved_chat_model", "service_router", "replay_archive"],
                ["approval trail", "policy decision", "replay record", "cost trace"],
            ),
        ],
    },
    "enterprise_operations": {
        "profile_name": "Enterprise Operations Workspace",
        "risk_tier": "medium",
        "policy_pack": "enterprise_operations_controls_v1",
        "policy_checks": [
            "Enforce approved model and tool list.",
            "Escalate cost spikes and unsupported public claims.",
        ],
        "evidence_requirements": [
            "approval trail",
            "policy decision",
            "model/tool used",
            "audit export",
            "cost trace",
        ],
        "restricted_actions": [
            "No unsupported compliance claims without founder review.",
        ],
        "recommended_model_tool_constraints": [
            "Prefer private runtime routes and approved internal tools.",
        ],
        "default_blocking_rules": [
            "Block unsupported public claims.",
            "Require review for high-risk customer-impacting actions.",
        ],
        "gpc_templates": [
            "Ops triage -> policy review -> approval -> deployment path",
        ],
        "sample_workflows": [
            "Support ticket triage",
            "Incident escalation summary",
        ],
        "suggested_demo_prompts": [
            "We want AI to triage support tickets, detect urgent issues, and route them with evidence.",
        ],
        "default_demo_scenarios": [
            _scenario(
                "ops_support_ticket_triage",
                "Support ticket triage",
                "Triage support tickets, detect urgent/security/compliance issues, summarize the case, and route it to the right team.",
                ["Read ticket", "Detect risk and urgency", "Summarize case", "Route to team", "Write replay evidence"],
                ["approved_chat_model", "ticket_router", "audit_archive"],
                ["approval trail", "policy decision", "model/tool used", "audit export", "cost trace"],
            ),
            _scenario(
                "ops_internal_policy_assistant",
                "Internal policy assistant",
                "Answer internal policy questions using approved models and tools only.",
                ["Retrieve policy source", "Answer with basis", "Escalate uncertainty", "Archive evidence"],
                ["approved_retrieval_model", "policy_index", "audit_export"],
                ["source references", "policy decision", "audit export", "versioned artifact"],
            ),
            _scenario(
                "ops_incident_escalation_summary",
                "Incident escalation summary",
                "Summarize internal incidents and route them based on urgency and risk.",
                ["Read incident", "Assess severity", "Summarize escalation", "Route to team", "Store replay evidence"],
                ["approved_chat_model", "incident_router", "replay_archive"],
                ["approval trail", "policy decision", "audit export", "cost trace"],
            ),
            _scenario(
                "ops_workflow_routing_assistant",
                "Workflow routing assistant",
                "Help operations teams route inbound work to the right queue while keeping an audit trail.",
                ["Read inbound work", "Classify route", "Route to team", "Archive evidence"],
                ["approved_chat_model", "workflow_router", "audit_archive"],
                ["approval trail", "policy decision", "audit export", "cost trace"],
            ),
        ],
    },
}


def normalize_industry(industry: str | None) -> str:
    value = str(industry or "").strip().lower()
    return value if value in SUPPORTED_INDUSTRIES else "generic"


def is_regulated_industry(industry: str | None) -> bool:
    return normalize_industry(industry) in REGULATED_INDUSTRIES


def _json_loads(value: str | None) -> Any | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def workspace_profile_defaults(industry: str | None) -> dict[str, Any]:
    normalized = normalize_industry(industry)
    template = deepcopy(PROFILE_TEMPLATES[normalized])
    return {
        "industry": normalized,
        "playground_profile": normalized,
        "risk_tier": template["risk_tier"],
        "default_policy_pack": template["policy_pack"],
        "default_demo_scenarios": template["default_demo_scenarios"],
        "default_evidence_requirements": template["evidence_requirements"],
        "default_blocking_rules": template["default_blocking_rules"],
    }


def ensure_workspace_profile_defaults(workspace: Workspace, industry: str | None = None) -> Workspace:
    defaults = workspace_profile_defaults(industry or getattr(workspace, "industry", None))
    workspace.industry = normalize_industry(getattr(workspace, "industry", None) or industry)
    workspace.playground_profile = getattr(workspace, "playground_profile", None) or defaults["playground_profile"]
    workspace.risk_tier = getattr(workspace, "risk_tier", None) or defaults["risk_tier"]
    workspace.default_policy_pack = getattr(workspace, "default_policy_pack", None) or defaults["default_policy_pack"]
    workspace.default_demo_scenarios = getattr(workspace, "default_demo_scenarios", None) or _json_dumps(defaults["default_demo_scenarios"])
    workspace.default_evidence_requirements = getattr(workspace, "default_evidence_requirements", None) or _json_dumps(defaults["default_evidence_requirements"])
    workspace.default_blocking_rules = getattr(workspace, "default_blocking_rules", None) or _json_dumps(defaults["default_blocking_rules"])
    return workspace


def resolve_workspace_profile(workspace: Workspace) -> dict[str, Any]:
    ensure_workspace_profile_defaults(workspace)
    industry = normalize_industry(workspace.industry)
    template = deepcopy(PROFILE_TEMPLATES[industry])
    scenarios = _json_loads(workspace.default_demo_scenarios) or template["default_demo_scenarios"]
    evidence_requirements = _json_loads(workspace.default_evidence_requirements) or template["evidence_requirements"]
    blocking_rules = _json_loads(workspace.default_blocking_rules) or template["default_blocking_rules"]
    risk_tier = (workspace.risk_tier or template["risk_tier"]).lower()
    profile_name = template["profile_name"]
    return {
        "workspaceId": workspace.id,
        "tenantId": workspace.id,
        "industry": industry,
        "playground_profile": workspace.playground_profile or industry,
        "profileName": profile_name,
        "risk_tier": risk_tier,
        "policy_pack": workspace.default_policy_pack or template["policy_pack"],
        "suggested_demo_prompts": template["suggested_demo_prompts"],
        "sample_workflows": template["sample_workflows"],
        "policy_checks": template["policy_checks"],
        "evidence_requirements": evidence_requirements,
        "gpc_templates": template["gpc_templates"],
        "restricted_actions": template["restricted_actions"],
        "recommended_model_tool_constraints": template["recommended_model_tool_constraints"],
        "default_demo_scenarios": scenarios,
        "default_blocking_rules": blocking_rules,
        "regulated_defaults": {
            "external_fallback_default": False if is_regulated_industry(industry) else True,
            "human_review_required_for_high_risk": True if is_regulated_industry(industry) else False,
            "evidence_capture_required": True if is_regulated_industry(industry) else True,
            "audit_replay_required": True if is_regulated_industry(industry) else False,
            "sensitive_data_warning_visible": True if is_regulated_industry(industry) else False,
            "founder_review_required_for_regulated_claims": True,
        },
    }


def find_profile_scenario(profile: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    for scenario in profile.get("default_demo_scenarios", []):
        if scenario.get("scenario_id") == scenario_id:
            return scenario
    raise KeyError(scenario_id)


def build_static_gpc_handoff(
    workspace: Workspace,
    *,
    scenario_id: str,
    scenario_title: str | None,
    user_input: str,
) -> dict[str, Any]:
    profile = resolve_workspace_profile(workspace)
    scenario = find_profile_scenario(profile, scenario_id)
    return {
        "workspaceId": workspace.id,
        "tenantId": workspace.id,
        "industry": profile["industry"],
        "playground_profile": profile["playground_profile"],
        "scenario_id": scenario["scenario_id"],
        "scenario_title": scenario_title or scenario["title"],
        "user_input": user_input,
        "risk_tier": profile["risk_tier"],
        "policy_pack": profile["policy_pack"],
        "evidence_requirements": profile["evidence_requirements"],
        "blocking_rules": profile["default_blocking_rules"],
        "suggested_workflow": scenario["suggested_workflow"],
        "suggested_models_tools": scenario["suggested_models_tools"],
        "handoff_status": "prepared",
        "claim_level": "draft",
    }


def dumps_payload(value: Any) -> str:
    return _json_dumps(value)
