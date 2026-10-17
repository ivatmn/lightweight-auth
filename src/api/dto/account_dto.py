# src/api/dto/account_dto.py
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=72)
    email: EmailStr | None = None
    full_name: str | None = None


class SignupResponse(BaseModel):
    id: int
    username: str


class OtpRequest(BaseModel):
    """Ask for an OTP to be generated (password reset or unlock)."""

    username: str


class OtpConfirmRequest(BaseModel):
    """Confirm an OTP for password reset or unlock."""

    username: str
    otp: str = Field(min_length=6, max_length=6)
    new_password: str | None = Field(default=None, min_length=8, max_length=72)


class MessageResponse(BaseModel):
    detail: str
