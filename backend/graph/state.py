from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    workflow_id: str
    current_node: str | None
    execution_status: str
    execution_log: list[str]
    executed_nodes: list[str]
    skipped_nodes: list[str]
    failed_node_ids: list[str]
    workflow_data: dict[str, Any]
    validation_passed: bool
    errors: list[str]
    inventory_checked: bool
    inventory_result: list[dict[str, Any]]
    vendor_selection_completed: bool
    selected_vendor: dict[str, Any] | None
    budget_validation_passed: bool
    total_cost: int | float
    budget_remaining: int | float
    approval_status: str
    approved_by: str | None
    approval_reason: str
    approval_timestamp: str
    approval_threshold: int | float
    purchase_order_generated: bool
    email_messages: list[dict[str, Any]]
    email_trigger_config: dict[str, Any]
    email_message_id: str | None
    email_sender: str | None
    email_recipient: str | None
    email_subject: str | None
    email_body: str | None
    email_received_at: str | None
    input_text: str
    workflow_status: str
    llm_output: str
    llm_provider: str
    llm_model: str
    llm_prompt: str
    llm_temperature: float
    llm_max_tokens: int
    recipient_email: str
    email_subject: str
    email_sent: bool
    email_sent_at: str | None
    email_status: str
    email_error: str | None
    purchase_order: dict[str, Any] | None
    purchase_order_number: str | None
    purchase_order_timestamp: str | None
    workflow_health: str
    completed_stages: list[str]
    failed_stages: list[str]
    skipped_stages: list[str]
    workflow_summary: str
    supervisor_timestamp: str
    failure_detected: bool
    failure_category: str
    failure_severity: str
    recoverable: bool
    failure_summary: str
    failure_timestamp: str
    failure_details: dict[str, Any]
    failure_context: dict[str, Any]
    supervisor_diagnosis: str
    incident_matches: list[dict[str, Any]]
    recommended_resolution: str
    knowledge_base_match_count: int
    rag_summary: str
    healing_attempted: bool
    healing_strategy: str
    healing_status: str
    healing_summary: str
    healing_timestamp: str
    next_recommended_action: str
    condition_result: bool
    condition_field: str
    condition_operator: str
    condition_value: str
    router_result: str
    classification: str
    classifier_input_field: str
    classifier_categories: list[str]
    classifier_provider: str
    classifier_model: str
    extracted_data: dict[str, Any]
    extractor_input_field: str
    extractor_fields: list[str]
    extractor_provider: str
    extractor_model: str
    summary: str
    summary_input_field: str
    summary_provider: str
    summary_model: str
