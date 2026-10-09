from app.pipelines.pipeline_manager import run_pipeline


def analyze_issue(text: str) -> dict[str, str]:
    return run_pipeline(text)
