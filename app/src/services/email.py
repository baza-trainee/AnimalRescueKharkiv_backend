import logging
from enum import Enum
from pathlib import Path
from typing import ClassVar, Dict

import uvicorn
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr
from src.auth.schemas import TokenBase
from src.configuration.settings import settings

logger = logging.getLogger(uvicorn.logging.__name__)

class EmailService:
    class EmailTemplate(Enum):
        INVITATION = 1
        WELCOME = 2
        RESET_PASS = 3
        PASS_CHANGED = 4

    __conf = ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_FROM_NAME=settings.mail_from_name,
        MAIL_STARTTLS=False,
        MAIL_SSL_TLS=True,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=Path(__file__).parent / "templates",
    )

    __templates: ClassVar[Dict[EmailTemplate, Dict[str, str]]] = {
        EmailTemplate.INVITATION: {"name": "invitation_email",
                                   "sub_EN": "Invitation to The Animal Rescue Kharkiv",
                                   "sub_UA": "Запрошення до Animal Rescue Kharkiv"},
        EmailTemplate.WELCOME: {"name": "welcome_email",
                                "sub_EN": "Welcome to The Animal Rescue Kharkiv",
                                "sub_UA": "Вітаємо у Команді Animal Rescue Kharkiv"},
        EmailTemplate.RESET_PASS: {"name": "reset_pass_email",
                                   "sub_EN": "Password Reset on The Animal Rescue Kharkiv",
                                   "sub_UA": "Відновлення Паролю на Animal Rescue Kharkiv"},
        EmailTemplate.PASS_CHANGED: {"name": "pass_changed_email",
                                     "sub_EN": "Password Reset Complited on The Animal Rescue Kharkiv",
                                     "sub_UA": "Успішна Зміна Паролю на Animal Rescue Kharkiv"},
    }

    async def send_email(
            self,
            email: EmailStr,
            template_body: Dict[str, str],
            template_name: EmailTemplate,
            token: TokenBase | None = None,
            language: str = "ua",
            ) -> None:
        """Sends an email with a verification token to the specified email address"""
        try:
            template = self.__templates[template_name]
            subject = template[f"sub_{language.upper()}"]
            template_body["subject"] = subject

            if token:
                template_body["token"] = token

            message = MessageSchema(
                subject=subject,
                recipients=[email],
                template_body=template_body,
                subtype=MessageType.html,
            )

            template_file = f"{template["name"]}_{language.upper()}.html"

            fm = FastMail(self.__conf)
            await fm.send_message(message, template_name=template_file)
            logger.info(f"{self.__class__.__name__}: {template_name.name} email sent")

        except ConnectionErrors as err:
            logger.error(err)

email_service: EmailService = EmailService()
