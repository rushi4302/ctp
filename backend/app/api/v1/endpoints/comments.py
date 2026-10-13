from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models import Comment, Report, User
from app.schemas.report import CommentCreate, CommentResponse

router = APIRouter(prefix="/comments")


@router.get("", response_model=List[CommentResponse])
def list_comments(report_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.moderation_status == "ACTIVE",
    ).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return (
        db.query(Comment)
        .options(joinedload(Comment.user))
        .filter(Comment.report_id == report_id)
        .order_by(Comment.created_at.asc())
        .all()
    )


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    data: CommentCreate,
    report_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.moderation_status == "ACTIVE",
    ).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    comment = Comment(report_id=report_id, user_id=user.id, content=data.content.strip())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
