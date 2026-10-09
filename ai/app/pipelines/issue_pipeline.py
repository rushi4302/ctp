from app.classifiers.issue_classifier import classify_issue
from app.preprocessing.text_processor import process_text
from app.severity.severity_predictor import predict_severity


def run_issue_pipeline(text: str) -> dict[str, str]:
    processed = process_text(text)
    classification = classify_issue(processed["text"])
    severity = predict_severity(classification["issue_type"])
    return {
        "status": processed["status"],
        "issue_type": classification["issue_type"],
        "severity": severity["severity"],
    }
