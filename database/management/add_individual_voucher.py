"""
Script to generate an individual competition voucher for a specific person.
"""
import argparse
import random
import uuid
from sqlmodel import Session, select
from utils.loggers import logger
from database.models.competitions import CompVoucher

# The specific competition ID to use for these vouchers
COMP_ID = uuid.UUID("74fbe3d5-4ca4-4dc0-9020-e98ba9e228a6")


def add_individual_voucher(session: Session,
                           full_name: str,
                           email: str = None,
                           phone: str = None):
    """
    Add an individual competition voucher for a specific person.

    Args:
        session: Database session
        full_name: Full name of the person
        email: Email address (optional)
        phone: Phone number (optional)
    """
    if not full_name or full_name.strip() == "":
        logger.error("Full name is required")
        return False

    # Check if a voucher already exists for this email (if provided)
    if email and email.strip() != "":
        existing_voucher = session.exec(
            select(CompVoucher).where(CompVoucher.competition_id == COMP_ID,
                                      CompVoucher.email == email)).first()

        if existing_voucher:
            logger.info(
                f"Voucher already exists for email {email}, skipping creation")
            logger.info("Existing voucher details - Name: "
                        f"{existing_voucher.full_name}, "
                        f"Code: {existing_voucher.code}")
            return False

    # Get all existing voucher codes to avoid duplicates
    existing_codes = {
        voucher.code
        for voucher in session.exec(
            select(CompVoucher).where(CompVoucher.competition_id == COMP_ID))
    }

    try:
        # Generate a unique 6-digit code
        while True:
            code = random.randint(100000, 999999)
            if code not in existing_codes:
                break

        # Create the voucher
        voucher = CompVoucher(id=uuid.uuid4(),
                              full_name=full_name.strip(),
                              email=email.strip() if email else None,
                              phone=phone.strip() if phone else None,
                              social_media=None,
                              code=code,
                              competition_id=COMP_ID)

        session.add(voucher)
        session.commit()

        logger.info(f"Added voucher for {full_name}")
        logger.info(f"Voucher code: {code}")

        return True

    except Exception as e:
        session.rollback()
        logger.error(f"Error adding voucher: {str(e)}")
        return False


if __name__ == "__main__":
    from database.management.base import get_db_session

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Add an individual competition voucher")
    parser.add_argument("--name",
                        required=True,
                        help="Full name of the person")
    parser.add_argument("--email", help="Email address (optional)")
    parser.add_argument("--phone", help="Phone number (optional)")

    args = parser.parse_args()

    # Add the voucher
    with get_db_session() as session:
        success = add_individual_voucher(session,
                                         full_name=args.name,
                                         email=args.email,
                                         phone=args.phone)

        if success:
            logger.info("Voucher added successfully")
        else:
            logger.warning("Failed to add voucher or voucher already exists")
