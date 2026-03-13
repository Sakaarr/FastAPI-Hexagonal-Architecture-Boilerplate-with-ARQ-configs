"""
╔══════════════════════════════════════════════════════════════╗
║  BACKGROUND TASK: Send Welcome Email                         ║
║                                                              ║
║  This is the actual async function that arq executes in      ║
║  the background worker process. It:                          ║
║  1. Builds an HTML welcome email                             ║
║  2. Sends it via SMTP (aiosmtplib)                           ║
║                                                              ║
║  In development, use MailHog (localhost:1025) to catch emails ║
║  without sending real mail.                                  ║
╚══════════════════════════════════════════════════════════════╝
"""

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

logger = logging.getLogger("app.tasks.email")


async def send_welcome_email(ctx: dict, email: str, name: str) -> str:
    """
    Background task: sends a welcome email to a newly created user.

    IMPORTANT — arq task signature:
    ────────────────────────────────
    - First argument is always `ctx` (arq context dict)
    - ctx contains anything you set up in on_startup
    - Remaining arguments are what you passed in enqueue()

    This function runs in the WORKER process, NOT in FastAPI.
    """
    settings = ctx.get("settings")
    if not settings:
        logger.error("❌ Settings not found in worker context")
        return "failed: no settings"

    # ── Build the email ──
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Welcome to {settings.app_name}, {name}! 🎉"
    msg["From"] = settings.smtp_sender
    msg["To"] = email

    # Plain text version
    text_body = f"""
Hi {name},

Welcome to {settings.app_name}!

Your account has been created successfully with the email: {email}

We're excited to have you on board. Here's what you can do next:
- Explore our API documentation at /docs
- Create your first product
- Check out the health endpoint at /health

If you have any questions, feel free to reach out.

Best regards,
The {settings.app_name} Team
    """.strip()

    # HTML version (email clients prefer this)
    html_body = f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background: #f4f7fa; padding: 40px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px;
                    box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden;">

            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 40px 30px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px;">
                    Welcome, {name}! 🎉
                </h1>
            </div>

            <div style="padding: 30px;">
                <p style="font-size: 16px; color: #333; line-height: 1.6;">
                    Your account has been created successfully at
                    <strong>{settings.app_name}</strong>.
                </p>

                <div style="background: #f8f9ff; border-left: 4px solid #667eea;
                            padding: 15px 20px; border-radius: 4px; margin: 20px 0;">
                    <p style="margin: 0; color: #555;">
                        📧 <strong>Email:</strong> {email}
                    </p>
                </div>

                <h3 style="color: #333; margin-top: 25px;">What's next?</h3>
                <ul style="color: #555; line-height: 2;">
                    <li>📖 Explore the API docs at <code>/docs</code></li>
                    <li>📦 Create your first product</li>
                    <li>💚 Check the health endpoint at <code>/health</code></li>
                </ul>
            </div>

            <div style="background: #f8f9fa; padding: 20px 30px; text-align: center;
                        font-size: 13px; color: #888;">
                Sent by {settings.app_name} • Powered by FastAPI + arq
            </div>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # ── Send the email ──
    try:
        logger.info(f"📧 Sending welcome email to {email}...")

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_use_tls,
        )

        logger.info(f"✅ Welcome email sent successfully to {email}")
        return f"sent to {email}"

    except Exception as e:
        logger.error(f"❌ Failed to send welcome email to {email}: {e}")
        # arq will log this as a failed job
        raise  # Re-raise so arq can handle retries
