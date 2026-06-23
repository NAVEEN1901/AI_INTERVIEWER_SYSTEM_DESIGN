"""Email Notification Service - sends automated emails for recruitment workflow."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from pathlib import Path

from jinja2 import Template

from app.core.config import settings

# Email templates
TEMPLATES = {
    "shortlisted": Template("""
<html>
<body>
<h2>Congratulations, {{ candidate_name }}!</h2>
<p>We are pleased to inform you that you have been <strong>shortlisted</strong> for the position of <strong>{{ job_title }}</strong> at {{ company_name }}.</p>

<h3>Next Steps:</h3>
<ul>
    <li>You will receive an interview invitation within the next 2-3 business days.</li>
    <li>Please ensure your profile is up to date.</li>
</ul>

<p>If you have any questions, please reply to this email.</p>

<p>Best regards,<br>{{ sender_name }}<br>Talent Acquisition Team</p>
</body>
</html>
"""),
    "interview_invite": Template("""
<html>
<body>
<h2>Interview Invitation</h2>
<p>Dear {{ candidate_name }},</p>
<p>You are invited to an interview for the position of <strong>{{ job_title }}</strong>.</p>

<h3>Interview Details:</h3>
<ul>
    <li><strong>Type:</strong> {{ interview_type }}</li>
    <li><strong>Date:</strong> {{ scheduled_date }}</li>
    <li><strong>Duration:</strong> {{ duration }} minutes</li>
    {% if interview_link %}<li><strong>Link:</strong> <a href="{{ interview_link }}">{{ interview_link }}</a></li>{% endif %}
</ul>

<p>Please confirm your availability by replying to this email.</p>

<p>Best regards,<br>{{ sender_name }}<br>Talent Acquisition Team</p>
</body>
</html>
"""),
    "rejection": Template("""
<html>
<body>
<p>Dear {{ candidate_name }},</p>
<p>Thank you for your interest in the <strong>{{ job_title }}</strong> position at {{ company_name }}.</p>
<p>After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match our current needs.</p>
<p>We encourage you to apply for future openings that match your skills and experience.</p>
<p>We wish you all the best in your career.</p>

<p>Best regards,<br>{{ sender_name }}<br>Talent Acquisition Team</p>
</body>
</html>
"""),
    "status_update": Template("""
<html>
<body>
<p>Dear {{ candidate_name }},</p>
<p>This is an update regarding your application for <strong>{{ job_title }}</strong>.</p>
<p><strong>Status:</strong> {{ status }}</p>
{% if message %}<p>{{ message }}</p>{% endif %}

<p>Best regards,<br>{{ sender_name }}<br>Talent Acquisition Team</p>
</body>
</html>
"""),
}


class EmailService:
    """SMTP email service for recruitment notifications."""

    def __init__(self):
        self.smtp_host = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(getattr(settings, "SMTP_PORT", 587))
        self.smtp_user = getattr(settings, "SMTP_USER", "")
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", "")
        self.from_email = getattr(settings, "FROM_EMAIL", self.smtp_user)
        self.company_name = getattr(settings, "COMPANY_NAME", "AI Talent Platform")

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> dict:
        """Send an email via SMTP."""
        if not self.smtp_user or not self.smtp_password:
            # Dev mode - log instead of sending
            return {
                "status": "simulated",
                "to": to_email,
                "subject": subject,
                "message": "Email not sent (SMTP not configured). Set SMTP_* env vars.",
            }

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())
            return {"status": "sent", "to": to_email, "subject": subject}
        except Exception as e:
            return {"status": "error", "to": to_email, "error": str(e)}

    def send_shortlisted_email(
        self,
        to_email: str,
        candidate_name: str,
        job_title: str,
        sender_name: str = "HR Team",
    ) -> dict:
        """Send shortlisting notification."""
        html = TEMPLATES["shortlisted"].render(
            candidate_name=candidate_name,
            job_title=job_title,
            company_name=self.company_name,
            sender_name=sender_name,
        )
        return self._send_email(
            to_email=to_email,
            subject=f"Congratulations! You've been shortlisted for {job_title}",
            html_body=html,
        )

    def send_interview_invite(
        self,
        to_email: str,
        candidate_name: str,
        job_title: str,
        interview_type: str = "AI-Powered Interview",
        scheduled_date: str = "TBD",
        duration: int = 30,
        interview_link: Optional[str] = None,
        sender_name: str = "HR Team",
    ) -> dict:
        """Send interview invitation."""
        html = TEMPLATES["interview_invite"].render(
            candidate_name=candidate_name,
            job_title=job_title,
            interview_type=interview_type,
            scheduled_date=scheduled_date,
            duration=duration,
            interview_link=interview_link,
            sender_name=sender_name,
        )
        return self._send_email(
            to_email=to_email,
            subject=f"Interview Invitation: {job_title}",
            html_body=html,
        )

    def send_rejection_email(
        self,
        to_email: str,
        candidate_name: str,
        job_title: str,
        sender_name: str = "HR Team",
    ) -> dict:
        """Send rejection notification."""
        html = TEMPLATES["rejection"].render(
            candidate_name=candidate_name,
            job_title=job_title,
            company_name=self.company_name,
            sender_name=sender_name,
        )
        return self._send_email(
            to_email=to_email,
            subject=f"Application Update: {job_title}",
            html_body=html,
        )

    def send_status_update(
        self,
        to_email: str,
        candidate_name: str,
        job_title: str,
        status: str,
        message: Optional[str] = None,
        sender_name: str = "HR Team",
    ) -> dict:
        """Send generic status update."""
        html = TEMPLATES["status_update"].render(
            candidate_name=candidate_name,
            job_title=job_title,
            status=status,
            message=message,
            sender_name=sender_name,
        )
        return self._send_email(
            to_email=to_email,
            subject=f"Application Status Update: {job_title}",
            html_body=html,
        )


# Singleton
email_service = EmailService()
