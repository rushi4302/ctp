"""Audit or replace only explicitly marked synthetic demo data in civic_db_test.

Run without arguments to print a read-only audit. Pass ``--apply`` to replace
the existing ``[SYNTHETIC DEMO ...]`` records with this 36-complaint dataset.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
import sys
import uuid

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.constants import CivicIssueStatus, ReportSeverity, ReportStatus
from app.core.roles import UserRole
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models import CivicIssue, CivicIssueStatusLog, Report, ReportMedia, ReportStatusLog, User
from app.services.ward_service import WardService


DEMO_PREFIX = "[SYNTHETIC DEMO "
DEMO_PHOTO_PREFIX = "synthetic-demo-"
NEW_FILES_ON_DISK: set[str] = set()

# Approximate locality centers used only to position clearly synthetic points
# on the demo map. They are not surveyed complaint locations or ward data.
LOCALITIES = {
    "Wagholi": (18.5800, 73.9800, ["Kesnand Road", "Wagholi Bazaar", "Nagar Road", "Awhalwadi Road", "Bakori Road"]),
    "Viman Nagar": (18.5679, 73.9143, ["Clover Park", "Datta Mandir Road", "Central Avenue", "Sakore Nagar", "Symbiosis Road"]),
    "Kharadi": (18.5515, 73.9348, ["Thite Nagar", "Chandan Nagar Road", "Rakshak Nagar", "EON access road", "Mundhwa-Kharadi Road"]),
    "Lohegaon": (18.6004, 73.9167, ["Porwal Road", "Airport Road", "Sant Nagar", "Dhanori-Lohegaon Road", "Kalwad Road"]),
    "Dhanori": (18.5971, 73.8870, ["Kalas Road", "Lohgaon Road", "Tingre Nagar edge", "Dhanori Jakat Naka", "New Airport Road"]),
}

# Each category has distinct issue descriptions and matching visual motifs.
SCENARIOS = {
    "Pothole/Road Damage": [
        ("Broken asphalt at a bus stop", "A broad asphalt depression has loose edges where buses pull in, forcing two-wheelers to swerve."),
        ("Ravelling beside a road junction", "A patch of road surface has broken into loose aggregate near the turn and is worsening after rain."),
        ("Sunken section across a lane", "A long sunken strip crosses the lane and causes a sharp bump for cycles and scooters."),
        ("Open-edged pothole near a crossing", "A deep pothole sits before the pedestrian crossing and is difficult to see after dusk."),
        ("Cracked pavement beside a drain", "The road edge has cracked and dropped beside a drain cover, leaving an uneven wheel path."),
        ("Damaged surface at a service road", "Several connected surface failures have made the service road rough and narrowed the safe route."),
    ],
    "Garbage": [
        ("Overflowing community bin", "The shared bin is full and mixed waste has spilled onto the footpath, blocking part of the walking route."),
        ("Uncollected waste at a corner", "Loose household waste and cardboard have accumulated at the street corner since the last collection."),
        ("Plastic litter beside a bus shelter", "Plastic packaging and disposable cups are scattered along the shelter edge and nearby pavement."),
        ("Debris around a collection point", "A pile of bagged waste and dry debris remains around the collection point and attracts stray animals."),
        ("Market-side waste accumulation", "Vegetable trimmings and packaging are piled beside the market lane and need routine collection."),
    ],
    "Water Leakage": [
        ("Water escaping from a roadside pipe", "A visible stream is escaping from a roadside pipe joint and forming a persistent puddle."),
        ("Leaking public tap connection", "Water continues to drip from the public tap connection after use and has softened the soil around it."),
        ("Wet patch over a buried supply line", "A recurring wet patch and small surface flow suggest a leak along the buried supply line."),
        ("Leaking valve chamber", "Water is seeping from the valve chamber cover and running across the edge of the road."),
        ("Supply pipe seepage near a footpath", "A narrow jet at the pipe connection keeps the footpath wet and slippery throughout the day."),
    ],
    "Streetlight Issue": [
        ("Streetlight not illuminating the lane", "The lamp head is dark after sunset, leaving the pedestrian lane poorly lit."),
        ("Flickering light near a junction", "The streetlight flickers repeatedly and does not provide steady illumination at the junction."),
        ("Damaged light fitting", "The light fitting appears damaged and the pole is not illuminating the pavement below."),
        ("Dark stretch beside a walkway", "Several steps of the walkway remain dark because the nearest streetlight is out."),
        ("Loose lamp head on a pole", "The lamp head is tilted and appears insecure; the light is also not working at night."),
    ],
    "Drainage Problem": [
        ("Blocked roadside drain", "Silt and refuse cover the drain opening, preventing runoff from entering the channel."),
        ("Sewage overflowing at a manhole", "Dark wastewater is escaping around the manhole rim and flowing toward the roadside."),
        ("Standing water above a clogged grate", "Water remains pooled over the grate after light rain, indicating a likely blockage."),
        ("Broken drain cover beside pavement", "The drain cover is displaced and leaves an exposed opening next to the walking path."),
        ("Drain channel carrying wastewater", "Wastewater is visible in the open channel and the flow is backing up near the outlet."),
    ],
    "Traffic Issue": [
        ("Damaged traffic signal housing", "The signal housing at the junction is visibly damaged and its indication is difficult to read."),
        ("Faded lane markings at a turn", "Lane markings have worn away at the turn, making vehicle paths unclear during busy periods."),
        ("Obstructed pedestrian crossing", "A temporary obstruction occupies the crossing approach and narrows the accessible route."),
        ("Missing sign at a road split", "The direction sign is missing at the road split, making the approach confusing to visitors."),
        ("Unsafe traffic island edge", "The traffic island edge is broken and loose pieces extend into the vehicle path."),
    ],
    "Other": [
        ("Damaged public bench", "A public seating bench has a broken slat and sharp exposed edges that make it unusable."),
        ("Broken bus shelter panel", "A shelter panel is cracked and partly detached beside the passenger waiting area."),
        ("Damaged pavement ramp", "The edge of the public access ramp is broken and creates a trip hazard for wheelchair users."),
        ("Loose public signpost base", "The signpost base is loose and leaning over the public path, requiring a safety inspection."),
        ("Broken park boundary railing", "A section of the public park railing is bent outward and leaves an exposed gap."),
    ],
}

STATUS_VALUES = (
    [CivicIssueStatus.PENDING.value] * 9
    + [CivicIssueStatus.ASSIGNED.value] * 7
    + [CivicIssueStatus.IN_PROGRESS.value] * 8
    + [CivicIssueStatus.RESOLVED.value] * 8
    + [CivicIssueStatus.CLOSED.value] * 4
)
SEVERITIES = [
    ReportSeverity.LOW.value,
    ReportSeverity.MEDIUM.value,
    ReportSeverity.MEDIUM.value,
    ReportSeverity.HIGH.value,
    ReportSeverity.CRITICAL.value,
    ReportSeverity.MEDIUM.value,
]
DEPARTMENTS = {
    "Pothole/Road Damage": "Roads (synthetic assignment)",
    "Garbage": "Solid Waste (synthetic assignment)",
    "Water Leakage": "Water Supply (synthetic assignment)",
    "Streetlight Issue": "Street Lighting (synthetic assignment)",
    "Drainage Problem": "Drainage (synthetic assignment)",
    "Traffic Issue": "Traffic (synthetic assignment)",
    "Other": "Public Works (synthetic assignment)",
}
REPORT_STATUS_FOR_ISSUE = {
    CivicIssueStatus.PENDING.value: ReportStatus.SUBMITTED.value,
    CivicIssueStatus.ASSIGNED.value: ReportStatus.VERIFIED.value,
    CivicIssueStatus.IN_PROGRESS.value: ReportStatus.IN_PROGRESS.value,
    CivicIssueStatus.RESOLVED.value: ReportStatus.RESOLVED.value,
    CivicIssueStatus.CLOSED.value: ReportStatus.RESOLVED.value,
}
HISTORY = [
    (CivicIssueStatus.PENDING.value, ReportStatus.SUBMITTED.value, 0),
    (CivicIssueStatus.ASSIGNED.value, ReportStatus.VERIFIED.value, 1),
    (CivicIssueStatus.IN_PROGRESS.value, ReportStatus.IN_PROGRESS.value, 3),
    (CivicIssueStatus.RESOLVED.value, ReportStatus.RESOLVED.value, 6),
    (CivicIssueStatus.CLOSED.value, ReportStatus.RESOLVED.value, 8),
]


@dataclass(frozen=True)
class DemoCase:
    index: int
    category: str
    title: str
    description: str
    locality: str
    landmark: str
    latitude: float
    longitude: float
    severity: str
    status: str
    age_days: int


def build_cases(now: datetime | None = None) -> list[DemoCase]:
    """Build deterministic, distinct synthetic complaint content and distribution."""
    now = now or datetime.now(timezone.utc)
    category_names = list(SCENARIOS)
    category_sequence = (category_names * 6)[:36]
    category_seen: Counter[str] = Counter()
    cases = []
    for index, category in enumerate(category_sequence):
        scenario_index = category_seen[category]
        category_seen[category] += 1
        issue_name, detail = SCENARIOS[category][scenario_index]
        locality = list(LOCALITIES)[index % len(LOCALITIES)]
        center_lat, center_lon, landmarks = LOCALITIES[locality]
        landmark = landmarks[(index // len(LOCALITIES) + scenario_index) % len(landmarks)]
        # Small repeatable offsets prevent marker overlap; they remain demo-only.
        offset = ((index % 3) - 1) * 0.00035
        status = STATUS_VALUES[index]
        marker = f"{DEMO_PREFIX}DATASET V2 {index + 1:03d}]"
        title = f"{marker} {issue_name} near {landmark}, {locality}"
        description = (
            f"{detail} Location: near {landmark}, {locality}, Pune. "
            "Synthetic demonstration record with approximate locality-center coordinates; "
            "not a citizen submission or verified municipal record."
        )
        cases.append(DemoCase(
            index=index,
            category=category,
            title=title,
            description=description,
            locality=locality,
            landmark=landmark,
            latitude=round(center_lat + offset, 6),
            longitude=round(center_lon - offset, 6),
            severity=SEVERITIES[index % len(SEVERITIES)],
            status=status,
            age_days=10 + ((index * 11) % 50),
        ))
    return cases


def _font(size: int) -> ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_demo_image(case: DemoCase, *, resolution: bool = False) -> bytes:
    """Render a distinct category-specific synthetic illustration, never a fake photo."""
    width, height = 960, 640
    image = Image.new("RGB", (width, height), (221, 234, 237))
    draw = ImageDraw.Draw(image)
    # Sky and simple Pune-like streetscape background.
    draw.rectangle((0, 0, width, 330), fill=(195, 222, 231))
    draw.rectangle((0, 300, width, 390), fill=(194, 185, 164))
    draw.polygon([(0, 390), (960, 390), (960, 640), (0, 640)], fill=(76, 78, 76))
    for x, color in [(35, (217, 194, 159)), (205, (188, 177, 155)), (710, (207, 191, 164)), (825, (184, 176, 160))]:
        draw.rectangle((x, 165, x + 115, 390), fill=color)
        for wy in range(195, 350, 48):
            draw.rectangle((x + 18, wy, x + 43, wy + 26), fill=(116, 153, 165))
            draw.rectangle((x + 66, wy, x + 91, wy + 26), fill=(116, 153, 165))

    # Road surface / local issue scene; each category gets a recognizable motif.
    if resolution:
        if case.category == "Pothole/Road Damage":
            draw.ellipse((350, 425, 605, 555), fill=(103, 105, 98))
            draw.line((380, 466, 575, 466), fill=(211, 202, 171), width=5)
        elif case.category == "Garbage":
            draw.rectangle((420, 420, 555, 558), fill=(88, 108, 91))
            draw.rectangle((406, 410, 568, 433), fill=(63, 78, 66))
        elif case.category == "Water Leakage":
            draw.rectangle((385, 410, 548, 445), fill=(110, 116, 116), outline=(52, 58, 58), width=5)
            draw.ellipse((405, 452, 535, 472), fill=(78, 80, 76))
        elif case.category == "Streetlight Issue":
            draw.rectangle((465, 175, 479, 505), fill=(62, 68, 68))
            draw.line((471, 190, 570, 190, 588, 210), fill=(62, 68, 68), width=13)
            draw.ellipse((565, 202, 610, 230), fill=(239, 209, 116), outline=(90, 81, 57), width=4)
        elif case.category == "Drainage Problem":
            draw.rectangle((330, 450, 650, 542), fill=(71, 78, 72), outline=(159, 151, 132), width=7)
            for x in range(350, 638, 34):
                draw.line((x, 460, x, 530), fill=(151, 158, 147), width=8)
        elif case.category == "Traffic Issue":
            draw.rectangle((510, 205, 524, 480), fill=(54, 61, 62))
            draw.rounded_rectangle((460, 165, 575, 275), radius=20, fill=(48, 54, 54), outline=(30, 34, 35), width=5)
            draw.ellipse((500, 243, 535, 257), fill=(71, 175, 90))
        else:
            draw.rectangle((300, 430, 665, 470), fill=(105, 77, 53))
            draw.rectangle((330, 468, 352, 548), fill=(76, 73, 67))
            draw.rectangle((605, 468, 628, 548), fill=(76, 73, 67))
    elif case.category == "Pothole/Road Damage":
        draw.ellipse((350, 425, 605, 555), fill=(44, 43, 42))
        draw.ellipse((375, 437, 565, 533), fill=(27, 29, 29))
        for n in range(7):
            x = 382 + ((n * 37 + case.index * 13) % 185)
            y = 450 + ((n * 17 + case.index * 7) % 68)
            draw.ellipse((x, y, x + 12, y + 7), fill=(147, 140, 124))
    elif case.category == "Garbage":
        draw.rectangle((420, 420, 555, 558), fill=(80, 91, 81))
        draw.rectangle((406, 410, 568, 433), fill=(53, 64, 58))
        for n in range(11):
            x = 335 + ((n * 47 + case.index * 19) % 285)
            y = 442 + ((n * 23 + case.index * 11) % 110)
            col = [(219, 181, 77), (165, 194, 183), (193, 113, 91), (230, 224, 205)][n % 4]
            draw.ellipse((x, y, x + 29, y + 21), fill=col, outline=(85, 83, 76))
    elif case.category == "Water Leakage":
        draw.rectangle((0, 468, width, 490), fill=(97, 99, 96))
        draw.rectangle((385, 410, 548, 445), fill=(110, 116, 116), outline=(52, 58, 58), width=5)
        draw.line((466, 445, 466, 520), fill=(67, 153, 197), width=16)
        draw.ellipse((340, 507, 595, 570), fill=(82, 159, 190))
        draw.ellipse((375, 518, 562, 555), fill=(120, 189, 207))
    elif case.category == "Streetlight Issue":
        draw.rectangle((465, 175, 479, 505), fill=(62, 68, 68))
        draw.line((471, 190, 570, 190, 588, 210), fill=(62, 68, 68), width=13)
        draw.ellipse((565, 202, 610, 230), fill=(62, 69, 71), outline=(36, 43, 45), width=4)
        draw.polygon([(535, 240), (625, 240), (688, 330), (475, 330)], fill=(42, 48, 49, 55))
        draw.ellipse((450, 490, 505, 511), fill=(149, 140, 113))
    elif case.category == "Drainage Problem":
        draw.rectangle((330, 450, 650, 542), fill=(49, 53, 50), outline=(159, 151, 132), width=7)
        for x in range(350, 638, 34):
            draw.line((x, 460, x, 530), fill=(131, 136, 129), width=8)
        draw.ellipse((250, 510, 710, 610), fill=(82, 120, 105))
        draw.line((270, 553, 690, 553), fill=(113, 155, 133), width=5)
    elif case.category == "Traffic Issue":
        draw.rectangle((510, 205, 524, 480), fill=(54, 61, 62))
        draw.rounded_rectangle((460, 165, 575, 275), radius=20, fill=(48, 54, 54), outline=(30, 34, 35), width=5)
        for y, col in [(190, (177, 60, 51)), (220, (211, 165, 66)), (250, (71, 143, 80))]:
            draw.ellipse((500, y - 7, 535, y + 7), fill=col)
        draw.line((120, 575, 315, 575), fill=(219, 207, 158), width=8)
    else:  # Other: damaged public infrastructure.
        draw.rectangle((300, 430, 665, 470), fill=(105, 77, 53))
        draw.rectangle((330, 468, 352, 548), fill=(76, 73, 67))
        draw.rectangle((605, 468, 628, 548), fill=(76, 73, 67))
        draw.line((422, 430, 440, 470), fill=(229, 224, 205), width=9)
        draw.line((445, 430, 424, 470), fill=(229, 224, 205), width=5)

    draw.rectangle((0, 0, width, 118), fill=(255, 255, 255))
    draw.text((32, 22), case.category, fill=(27, 53, 61), font=_font(35))
    draw.text((34, 72), f"{case.locality}, Pune | Synthetic demonstration illustration", fill=(60, 88, 95), font=_font(20))
    draw.text((34, 98), case.title.split("] ", 1)[-1], fill=(60, 88, 95), font=_font(16))
    if resolution:
        draw.rounded_rectangle((650, 30, 925, 64), radius=12, fill=(42, 123, 102))
        draw.text((666, 38), "CONCEPTUAL AFTER VIEW", fill="white", font=_font(17))
    draw.rectangle((0, height - 54, width, height), fill=(33, 45, 48))
    draw.text((30, height - 42), "SYNTHETIC DATA - NOT A CITIZEN PHOTO OR MUNICIPAL WORK EVIDENCE", fill="white", font=_font(18))
    output = BytesIO()
    image.save(output, format="JPEG", quality=88, optimize=True)
    return output.getvalue()


def audit_database(db: Session) -> dict:
    demo_reports = db.query(Report).filter(Report.title.like(f"{DEMO_PREFIX}%")).all()
    demo_issues = db.query(CivicIssue).filter(CivicIssue.title.like(f"{DEMO_PREFIX}%")).all()
    return {
        "reports_total": db.query(Report).count(),
        "issues_total": db.query(CivicIssue).count(),
        "marked_demo_reports": len(demo_reports),
        "marked_demo_issues": len(demo_issues),
        "unmarked_reports_preserved": db.query(Report).filter(~Report.title.like(f"{DEMO_PREFIX}%")).count(),
        "unmarked_issues_preserved": db.query(CivicIssue).filter(~CivicIssue.title.like(f"{DEMO_PREFIX}%")).count(),
        "demo_categories": dict(Counter(report.category for report in demo_reports)),
        "demo_statuses": dict(Counter(issue.status for issue in demo_issues)),
    }


def _make_demo_users(db: Session) -> list[User]:
    users = []
    for index in range(1, 7):
        email = f"demo.citizen{index}@synthetic.civic.org"
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None:
            # Preserve and reuse the explicitly marked accounts from the old seed.
            legacy_email = f"demo.citizen{index}@synthetic.civic.test"
            user = db.query(User).filter(User.email == legacy_email).one_or_none()
            if user is not None:
                user.email = email
                db.flush()
        if user is None:
            user = User(
                full_name=f"Synthetic Demo Citizen {index}",
                email=email,
                hashed_password=hash_password(uuid.uuid4().hex + "aA1!"),
                role=UserRole.CITIZEN,
                is_active=True,
            )
            db.add(user)
            db.flush()
        users.append(user)
    return users


def _status_events(final_status: str) -> list[tuple[str, str, int]]:
    last_index = next(i for i, (issue_status, _, _) in enumerate(HISTORY) if issue_status == final_status)
    return HISTORY[: last_index + 1]


def replace_demo_dataset(db: Session) -> dict:
    """Replace only title-marked demo rows; preserve all unmarked reports/issues/users."""
    old_reports = db.query(Report).filter(Report.title.like(f"{DEMO_PREFIX}%")).all()
    old_issues = db.query(CivicIssue).filter(CivicIssue.title.like(f"{DEMO_PREFIX}%")).all()
    old_file_names = {media.file_name for report in old_reports for media in report.media}
    old_file_names.update(
        (issue.resolution_evidence_url or "").rsplit("/", 1)[-1]
        for issue in old_issues if issue.resolution_evidence_url
    )

    old_report_ids = {report.id for report in old_reports}
    affected_issue_ids = {report.civic_issue_id for report in old_reports if report.civic_issue_id is not None}
    # A marked issue linked to any unmarked report is ambiguous: retain that issue.
    deletable_issue_ids = {
        issue.id for issue in old_issues
        if all(report.id in old_report_ids for report in issue.reports)
    }
    for report in old_reports:
        db.delete(report)
    for issue in old_issues:
        if issue.id in deletable_issue_ids:
            db.delete(issue)

    for issue_id in affected_issue_ids - deletable_issue_ids:
        affected_issue = db.get(CivicIssue, issue_id)
        if affected_issue is not None:
            affected_issue.report_count = db.query(Report.id).filter(Report.civic_issue_id == issue_id).count()

    users = _make_demo_users(db)
    cases = build_cases()
    upload_dir = Path(settings.upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    new_file_names: set[str] = set()
    for case in cases:
        file_name = f"{DEMO_PHOTO_PREFIX}{uuid.uuid4().hex}.jpg"
        image_bytes = render_demo_image(case)
        new_file_names.add(file_name)
        NEW_FILES_ON_DISK.add(file_name)
        (upload_dir / file_name).write_bytes(image_bytes)

        is_resolved = case.status in {CivicIssueStatus.RESOLVED.value, CivicIssueStatus.CLOSED.value}
        resolution_file_name = None
        if is_resolved and case.index % 2 == 0:
            resolution_file_name = f"{DEMO_PHOTO_PREFIX}{uuid.uuid4().hex}-concept.jpg"
            resolution_bytes = render_demo_image(case, resolution=True)
            new_file_names.add(resolution_file_name)
            NEW_FILES_ON_DISK.add(resolution_file_name)
            (upload_dir / resolution_file_name).write_bytes(resolution_bytes)

        created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=case.age_days)
        reporter = users[case.index % len(users)]
        ward = WardService.assign_ward(case.latitude, case.longitude)
        issue = CivicIssue(
            title=case.title,
            description=case.description,
            category=case.category,
            status=case.status,
            severity=case.severity,
            latitude=case.latitude,
            longitude=case.longitude,
            locality=case.locality,
            city="Pune",
            district="Pune",
            state="Maharashtra",
            ward=ward,
            report_count=1,
            resolution_notes=(
                "Synthetic conceptual after-view for demonstration only; it does not document real municipal work."
                if resolution_file_name else None
            ),
            resolution_evidence_url=f"/uploads/{resolution_file_name}" if resolution_file_name else None,
            assigned_department_id=DEPARTMENTS[case.category] if case.status != CivicIssueStatus.PENDING.value else None,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(issue)
        db.flush()
        report = Report(
            civic_issue_id=issue.id,
            title=case.title,
            description=case.description,
            category=case.category,
            status=REPORT_STATUS_FOR_ISSUE[case.status],
            severity=case.severity,
            latitude=case.latitude,
            longitude=case.longitude,
            address=f"Near {case.landmark}, {case.locality}",
            locality=case.locality,
            city="Pune",
            district="Pune",
            state="Maharashtra",
            ward=ward,
            reporter_id=reporter.id,
            assigned_department_id=issue.assigned_department_id,
            location_validation_status="MISSING_METADATA",
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(report)
        db.flush()
        db.add(ReportMedia(
            report_id=report.id,
            file_url=f"/uploads/{file_name}",
            file_name=file_name,
            file_type="image/jpeg",
            file_size=len(image_bytes),
            created_at=created_at,
        ))

        previous_issue_status = "NONE"
        previous_report_status = "NONE"
        last_event_at = created_at
        for issue_status, report_status, day_offset in _status_events(case.status):
            event_at = created_at + timedelta(days=day_offset)
            last_event_at = event_at
            comment = "Synthetic lifecycle event for research/demo; not an official municipal action."
            db.add(CivicIssueStatusLog(
                civic_issue_id=issue.id,
                changed_by_id=reporter.id,
                previous_status=previous_issue_status,
                new_status=issue_status,
                comment=comment,
                created_at=event_at,
            ))
            db.add(ReportStatusLog(
                report_id=report.id,
                changed_by_id=reporter.id,
                previous_status=previous_report_status,
                new_status=report_status,
                comment=comment,
                created_at=event_at,
            ))
            previous_issue_status = issue_status
            previous_report_status = report_status
        issue.updated_at = last_event_at
        report.updated_at = last_event_at
        if case.status in {CivicIssueStatus.RESOLVED.value, CivicIssueStatus.CLOSED.value}:
            issue.resolved_at = last_event_at
            if case.status == CivicIssueStatus.CLOSED.value:
                issue.closed_at = last_event_at + timedelta(days=1)
                issue.updated_at = issue.closed_at

    try:
        db.commit()
    except Exception:
        db.rollback()
        for name in new_file_names:
            (upload_dir / name).unlink(missing_ok=True)
            NEW_FILES_ON_DISK.discard(name)
        raise
    NEW_FILES_ON_DISK.difference_update(new_file_names)
    # Remove only files formerly referenced by marked demo records and only if
    # no surviving report/evidence row refers to them.
    referenced = {name for (name,) in db.query(ReportMedia.file_name).all()}
    referenced.update(
        (url or "").rsplit("/", 1)[-1]
        for (url,) in db.query(CivicIssue.resolution_evidence_url).filter(CivicIssue.resolution_evidence_url.isnot(None)).all()
    )
    for name in old_file_names - referenced:
        target = (upload_dir / name).resolve()
        if target.parent == upload_dir and target.is_file():
            target.unlink(missing_ok=True)
    return {"created": len(cases), "files": new_file_names, "cases": cases}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="replace only explicitly marked synthetic demo records")
    args = parser.parse_args()
    database_name = make_url(settings.database_url).database
    if database_name != "civic_db_test":
        raise SystemExit("Refusing to connect: this script is restricted to civic_db_test")

    db = SessionLocal()
    try:
        audit = audit_database(db)
        print("Read-only audit of civic_db_test:")
        for key, value in audit.items():
            print(f"  {key}: {value}")
        if not args.apply:
            print("No records changed. Re-run with --apply to replace only title-marked synthetic demo records.")
            return
        result = replace_demo_dataset(db)
        print(f"Replaced marked demo data with {result['created']} synthetic complaints.")
        print(f"Category distribution: {dict(Counter(case.category for case in result['cases']))}")
        print(f"Status distribution: {dict(Counter(case.status for case in result['cases']))}")
        print(f"Synthetic issue illustrations stored: {len(result['files'])}")
    except Exception:
        db.rollback()
        failed_upload_dir = Path(settings.upload_dir).resolve()
        for name in NEW_FILES_ON_DISK:
            (failed_upload_dir / name).unlink(missing_ok=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
