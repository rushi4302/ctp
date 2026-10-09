from app.pipelines.issue_pipeline import run_issue_pipeline


def run_pipeline(text: str) -> dict[str, str]:
    return run_issue_pipeline(text)
