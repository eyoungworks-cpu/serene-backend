"""
Serene Account Creation Service
Handles:
- Request validation
- Asylum approval
- Guardian security checks
- Account registry logging
"""

import csv
import datetime
from pathlib import Path

from governance.governance_loader import (
    load_governance,
    get_governance,
    ACCOUNT_REGISTRY_PATH
)

# Load governance data
gov = load_governance()


class AccountRequestError(Exception):
    """Raised when an account request is invalid."""
    pass


def validate_request(request: dict):
    """Ensure Serene's request includes all required fields."""
    required = gov["governance"]["serene"]["account_creation_requirements"]

    missing = [field for field in required if field not in request or not request[field]]
    if missing:
        raise AccountRequestError(f"Missing required fields: {', '.join(missing)}")

    return True


def asylum_approval(request: dict):
    """
    Asylum approves the need for the account.
    This is where Asylum's logic will plug in later.
    For now, this is a placeholder that always approves.
    """

    # Example logic Asylum will eventually replace:
    if "purpose" not in request or len(request["purpose"]) < 5:
        raise AccountRequestError("Purpose too vague for Asylum approval.")

    approval_id = f"APPROVED-{datetime.datetime.utcnow().timestamp()}"
    return approval_id


def guardian_security_check(request: dict):
    """
    Guardian checks for security risks.
    This is a placeholder for future Guardian logic.
    """

    sensitive_keywords = ["PII", "financial", "medical", "restricted"]

    if any(word.lower() in request["purpose"].lower() for word in sensitive_keywords):
        raise AccountRequestError("Guardian flagged this request as high-risk.")

    return True


def write_to_registry(request: dict, approval_id: str):
    """Append the new account to the registry CSV."""
    registry_path = Path(ACCOUNT_REGISTRY_PATH)

    row = [
        request["platform"],
        request.get("username", ""),
        request["owner"],
        request["purpose"],
        datetime.datetime.utcnow().isoformat(),
        "Serene",
        approval_id,
        request["expected_roi"],
        "",
        "active"
    ]

    # Ensure directory exists
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    # Append to CSV
    write_header = not registry_path.exists()

    with open(registry_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow([
                "platform", "username", "owner", "purpose",
                "date_created", "created_by", "asylum_approval_id",
                "expected_roi", "roi_notes", "status"
            ])
        writer.writerow(row)


def create_account(request: dict):
    """
    Main entry point for Serene.
    Validates → Asylum approves → Guardian checks → Registry logs.
    """

    # Step 1: Validate request
    validate_request(request)

    # Step 2: Asylum approval
    approval_id = asylum_approval(request)

    # Step 3: Guardian security check
    guardian_security_check(request)

    # Step 4: Log to registry
    write_to_registry(request, approval_id)

    return {
        "status": "success",
        "approval_id": approval_id,
        "message": f"Account for {request['platform']} approved and logged."
    }
