from dataclasses import dataclass

from src.configuration.settings import settings


@dataclass(frozen=True)
class ReturnMessages:
    user_logout: str = "Successfully logged out"
    user_logout_failed: str = "Logout failed"
    user_not_found: str = "User '%s' not found"
    user_reg_failed: str = "User registration failed with error: %s"
    user_duplicate: str = "User '%s' already exists in '%s' domain"
    user_pwd_invalid: str = settings.password_incorrect_message
    user_phone_invalid: str = settings.phone_invalid_message
    user_email_invalid: str = "Emails with the following domains are not allowed: %s"
    user_email_invalid_format: str = settings.email_invalid_format_message

    email_invalid: str = "Invalid email"
    email_sent: str = "%s email sent successfully"
    email_failed: str = "%s email failed to send"

    pwd_invalid: str = "Invalid password"
    pwd_changed: str = "Password changed successfully"
    pwd_change_failed: str = "Failed to change password"
    pwd_not_match: str = "Passwords do not match"

    token_invalid: str = "Invalid token"
    token_refresh_missing: str = "Refresh token missing"
    token_access_missing: str = "Access token missing"
    token_email_invalid: str = "Email does not match the token"
    token_scope_invalid: str = "Invalid scope in the token"
    token_credentials_error: str = "Could not validate credentials from token"

    media_not_found: str = "Media asset not found"
    media_blob_not_found: str = "Media blob not found"

    perm_not_found: str = "Permission not found"

    role_not_found: str = "Role not found"

    access_denied: str = "Access denied. Required permissions: %s"

    illegal_sort: str = "Sort expression should be in format {field}|{direction}"
    illegal_sort_field_name:str = "Can't sort results by invalid '%s' field"

    crm_animal_type_not_found: str = "Animal type not found"
    crm_animal_not_found: str = "Animal not found"
    crm_location_not_found: str = "Location not found"
    crm_lock_not_found: str = "Section '%s' is not locked by user '%s'"
    crm_acquire_lock_failed: str = "Failed to acquire lock on '%s' section for '%s' user"
    crm_invalid_date_format: str = "Invalid date format. Expected string in DD/MM/YYYY or YYYY-MM-DD format."
    crm_date_range_invalid: str = "The '%s' value cannot be less than the '%s' one"

    non_empty_string: str = "String should not be empty"
    definition_for_model_not_found: str = "Definition id='%d' referenced in the field '%s' not found"

    date_not_past_present: str = "Date must be in the past or today"


RETURN_MSG = ReturnMessages()
