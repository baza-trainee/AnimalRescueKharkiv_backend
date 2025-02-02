from dataclasses import dataclass


@dataclass(frozen=True)
class ReturnMessages:
    user_logout: str = "Successfully logged out"
    user_logout_failed: str = "Logout failed"
    user_not_found: str = "User '%s' not found"
    user_reg_failed: str = "User registration failed with error: %s"
    user_duplicate: str = "User '%s' already exists in '%s' domain"

    email_invalid: str = "Invalid email"
    email_sent: str = "%s email sent successfully"
    email_failed: str = "%s email failed to send"

    pwd_invalid: str = "Invalid password"
    pwd_changed: str = "Password changed successfully"
    pwd_change_failed: str = "Failed to change password"
    pwd_not_match: str = "Passwords do not match"

    token_invalid: str = "Invalid token"
    token_email_invalid: str = "Email does not match the token"
    token_scope_invalid: str = "Invalid scope in the token"
    token_credentials_error: str = "Could not validate credentials from token"

    media_not_found: str = "Media asset not found"
    media_blob_not_found: str = "Media blob not found"

    perm_not_found: str = "Permission not found"

    role_not_found: str = "Role not found"

    access_denied: str = "Access denied. Required permissions: %s"

    crm_animal_type_not_found: str = "Animal type not found"
    crm_animal_not_found: str = "Animal not found"
    crm_location_not_found: str = "Location not found"
    crm_illegal_sort: str = "Sort expression should be in format {field}|{direction}"


RETURN_MSG = ReturnMessages()
