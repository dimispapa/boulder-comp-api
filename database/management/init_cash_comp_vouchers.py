"""
Script to generate 100 competition vouchers with CASH naming pattern.
"""
from sqlmodel import Session, select
import random
import uuid
from utils.loggers import logger
from database.models.competitions import CompVoucher

# The specific competition ID to use for these vouchers
COMP_ID = uuid.UUID("74fbe3d5-4ca4-4dc0-9020-e98ba9e228a6")


def generate_cash_vouchers(session: Session):
    """Generate 100 competition vouchers with CASH naming pattern
    for a specific competition."""
    # Check if vouchers already exist for this competition
    existing_vouchers = session.exec(
        select(CompVoucher).where(
            CompVoucher.competition_id == COMP_ID)).all()

    # Get existing voucher codes to avoid duplicates
    existing_codes = {voucher.code for voucher in existing_vouchers}

    if len(existing_vouchers) >= 100:
        logger.info(f"Already have {len(existing_vouchers)} vouchers "
                    "for this competition, skipping generation")
        return

    try:
        # Generate a set of unique 6-digit codes
        vouchers = []
        vouchers_to_create = 100 - len(existing_vouchers)

        logger.info(f"Generating {vouchers_to_create} new vouchers "
                    f"for competition {COMP_ID}")

        # Check the highest CASH number already used
        cash_numbers = []
        for voucher in existing_vouchers:
            if voucher.full_name and voucher.full_name.startswith("CASH"):
                try:
                    num = int(
                        voucher.full_name[4:])  # Extract number from "CASH123"
                    cash_numbers.append(num)
                except ValueError:
                    pass

        # Start from the next number after the highest one used
        start_number = 1
        if cash_numbers:
            start_number = max(cash_numbers) + 1

        for i in range(start_number, start_number + vouchers_to_create):
            # Generate a unique 6-digit code
            while True:
                code = random.randint(100000, 999999)
                if code not in existing_codes:
                    existing_codes.add(code)
                    break

            # Create voucher with CASH naming pattern
            voucher = CompVoucher(id=uuid.uuid4(),
                                  full_name=f"CASH{i}",
                                  email=None,
                                  phone=None,
                                  social_media=None,
                                  code=code,
                                  competition_id=COMP_ID)
            vouchers.append(voucher)

        if vouchers:
            session.add_all(vouchers)
            session.commit()
            logger.info(f"Added {len(vouchers)} CASH vouchers "
                        f"for competition {COMP_ID}")
        else:
            logger.info("No new vouchers needed to be created")

    except Exception as e:
        session.rollback()
        logger.error(f"Error generating CASH vouchers: {str(e)}")


def initialize_cash_vouchers(session: Session):
    """Initialize cash vouchers - function name follows
    the pattern used in other scripts."""
    generate_cash_vouchers(session)


if __name__ == "__main__":
    from database.management.base import get_db_session

    # When run directly, initialize the cash vouchers
    with get_db_session() as session:
        initialize_cash_vouchers(session)
        logger.info("Cash vouchers initialization complete!")
