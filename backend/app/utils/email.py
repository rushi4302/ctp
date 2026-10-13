import logging
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_mail_config() -> ConnectionConfig | None:
    if not settings.mail_username or not settings.mail_server:
        return None
    return ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from or settings.mail_username,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=bool(settings.mail_username and settings.mail_password),
        VALIDATE_CERTS=True,
    )


async def send_reset_email(email: EmailStr, token: str):
    conf = get_mail_config()
    if not conf:
        logger.warning("Password reset email was not sent because mail is not configured.")
        return

    reset_link = f"http://localhost:3000/reset-password?token={token}"

    message = MessageSchema(
        subject="Reset Your Password",
        recipients=[email],
        body=f"""Hello,

You requested a password reset for Civic Intelligence Platform.

Click the link below or copy it to your browser:
{reset_link}

This link expires in 30 minutes.

If you did not request this, simply ignore this email.

Thanks,
Civic Intelligence Platform
""",
        subtype=MessageType.plain,
    )

    try:
        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(f"Password reset email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send reset email to {email}: {e}")
