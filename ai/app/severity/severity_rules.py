def apply_severity_rules(issue_type: str) -> str:
    return "medium" if issue_type else "low"
