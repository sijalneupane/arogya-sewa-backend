from typing import Any

from pydantic import BaseModel, EmailStr, Field


class SendTextEmailRequest(BaseModel):
    to: list[EmailStr] = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class SendHtmlEmailRequest(BaseModel):
    to: list[EmailStr] = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    html: str = Field(..., min_length=1)
    text_fallback: str | None = None


class SendTemplateEmailRequest(BaseModel):
    to: list[EmailStr] = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    template: str = Field(..., min_length=1)
    template_variables: dict[str, Any] = Field(default_factory=dict)


class SendEmailResponse(BaseModel):
    id: str | None = None
    message: str


class MailgunWebhookResponse(BaseModel):
    status: str
