from app.config.settings import settings
from app.services.ai_service import analyze_issue


def main() -> dict[str, object]:
    sample_result = analyze_issue("Pothole reported near the main road")
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "sample_result": sample_result,
    }


if __name__ == "__main__":
    print(main())
