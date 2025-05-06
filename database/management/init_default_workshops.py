"""
Database initialization for default workshop data.
"""
from sqlmodel import Session, select
from datetime import datetime, UTC
import pytz

from utils.loggers import logger
from database.models.enums import EventStatus
from database.models.workshops import Workshop

# Constants for workshop default values
DEFAULT_VENUE = "Inia-Droushia Bouldering Area"

# Workshop data
WORKSHOP_DATA = [
    {
        "name": "climbing-photography",
        "display_name": "Introduction to Adventure Photography",
        "start_date": datetime(2025, 5, 18, 9, 0),
        "payment_link_id": "plink_1RJyD2B2WPnInsslsu0u3Owc",
        "payment_link": "https://book.stripe.com/14kfZO5KC6Am5ribIM",
        "max_participants": 8,
    },
    {
        "name": "intro-to-outdoor-bouldering-adults",
        "display_name": "Intro to Outdoor Bouldering – Adults (18+)",
        "start_date": datetime(2025, 5, 17, 11, 00),
        "payment_link_id": "plink_1RJyBGB2WPnInssl1yzoskOf",
        "payment_link": "https://book.stripe.com/4gw9Bqa0S6Am6vmdQT",
        "max_participants": 15,
    },
    {
        "name": "guided-highline-session",
        "display_name": "Guided Highline Session - Alikou, Inia",
        "start_date": datetime(2025, 5, 18, 11, 0),
        "payment_link_id": "plink_1RJy7TB2WPnInsslS1UzcKyX",
        "payment_link": "https://book.stripe.com/6oE5la5KCgaWbPG002",
        "max_participants": 15,
    },
    {
        "name": "intro-to-outdoor-bouldering-kids",
        "display_name": "Intro to Outdoor Bouldering – Kids (12–16)",
        "start_date": datetime(2025, 5, 17, 11, 00),
        "payment_link_id": "plink_1RJBykB2WPnInsslgmKukBF9",
        "payment_link": "https://book.stripe.com/6oEaFugpg9My06YfYZ",
        "max_participants": 20,
    },
    {
        "name": "intro-to-sport-climbing",
        "display_name": "Intro to Sport Climbing – Gerakopetra, Inia",
        "start_date": datetime(2025, 5, 18, 10, 0),
        "payment_link_id": "plink_1RJBg7B2WPnInsslJUeTqBKi",
        "payment_link": "https://book.stripe.com/cN28xm2yqcYK5ricMM",
        "max_participants": 30,
    },
]

# Workshop descriptions
WORKSHOP_DESCRIPTIONS = {
    "Introduction to Adventure Photography":
    "A workshop on adventure photography with a special focus on climbing."
    "This workshop covers shooting techniques, composition, lighting, "
    "equipment, moving safely on rock, and a Q&A session. No prior "
    "experience with rappelling techniques is required, "
    "but it can be helpful.",
    "Intro to Outdoor Bouldering – Adults (18+)":
    "This workshop introduces adults to the fundamentals of outdoor "
    "bouldering. You'll learn safety, basic movement skills, spotting, and "
    "bouldering etiquette. Perfect for beginners or those transitioning from "
    "indoor to outdoor climbing. Please bring your own climbing shoes, as "
    "there will be a limited number of shoes available for use.",
    "Guided Highline Session - Alikou, Inia":
    "Experience the thrill of highlining with the guidance of Cyprus' "
    "pioneers of highlining. This session covers safety protocols, "
    "basic walking techniques, and mental preparation. No prior experience "
    "necessary, but participants should ideally be comfortable with heights.",
    "Intro to Outdoor Bouldering – Kids (10–16)":
    "A fun and engaging introduction to outdoor bouldering designed "
    "specifically for young climbers. Children will learn climbing basics, "
    "safety, and environmental awareness through games and supervised "
    "climbing. All equipment provided. Parental consent required.",
    "Intro to Sport Climbing – Gerakopetra, Inia":
    "Learn the essentials of sport climbing at the beautiful "
    "Gerakopetra crag. This workshop covers safety, belaying, top-roping, "
    "route reading and basic movement skills. Suitable for beginners. "
    "Equipment available if needed."
}

# Workshop instructors
WORKSHOP_INSTRUCTORS = {
    "Climbing Photography Workshop":
    "Chrisostomos Kamberis",
    "Intro to Outdoor Bouldering – Adults (18+)":
    "Paris Hadjisoteriou (Redpoint Academy Nicosia)",
    "Guided Highline Session - Alikou, Inia":
    "Kim Lucas, Theo Constantinou & Tanios Nassar",
    "Intro to Outdoor Bouldering – Kids (10–16)":
    "Constantinos Prodromou & others (Mountain Junkies)",
    "Intro to Sport Climbing – Gerakopetra, Inia":
    "Marios Hadjipetris (One Step Further) & "
    "Petros Christoforou (Elephant Monkey)"
}

# Workshop fees in EUR
WORKSHOP_FEES = {
    "Climbing Photography Workshop": 10.00,
    "Intro to Outdoor Bouldering – Adults (18+)": 10.00,
    "Guided Highline Session - Alikou, Inia": 10.00,
    "Intro to Outdoor Bouldering – Kids (10–16)": 10.00,
    "Intro to Sport Climbing – Gerakopetra, Inia": 10.00
}


def create_default_workshops(session: Session):
    """
    Create default workshops using hard-coded data.

    Args:
        session: Database session
    """
    workshops = []

    for workshop_data in WORKSHOP_DATA:
        display_name = workshop_data["display_name"]
        name = workshop_data["name"]
        payment_link_id = workshop_data["payment_link_id"]
        payment_link = workshop_data["payment_link"]
        max_participants = workshop_data["max_participants"]

        # Generate start date in UTC
        local_tz = pytz.timezone('Europe/Nicosia')
        aware_start = local_tz.localize(workshop_data["start_date"])
        start_date = aware_start.astimezone(UTC)

        # Get description, instructor and fee
        description = WORKSHOP_DESCRIPTIONS.get(display_name, "")
        instructor = WORKSHOP_INSTRUCTORS.get(display_name, "")
        fee = WORKSHOP_FEES.get(display_name, 0.0)

        # Create workshop object
        workshop = Workshop(name=name,
                            display_name=display_name,
                            payment_link_id=payment_link_id,
                            payment_link=payment_link,
                            start_date=start_date,
                            status=EventStatus.upcoming,
                            description=description,
                            venue=DEFAULT_VENUE,
                            max_participants=max_participants,
                            fee=fee,
                            instructor=instructor)

        workshops.append(workshop)
        logger.info(f"Prepared workshop: {display_name} "
                    f"({start_date.strftime('%Y-%m-%d')})")

    # Add all workshops to the database
    session.add_all(workshops)
    session.commit()
    logger.info(f"Successfully created {len(workshops)} default workshops")


def initialize_default_workshops(session: Session):
    """
    Initialize the database with default workshop data.

    Args:
        session: Database session
    """
    # Check if workshops already exist
    existing_count = session.exec(select(Workshop)).first()
    if existing_count:
        logger.info("Workshops already exist in database, skipping import")
        return

    # Create default workshops
    create_default_workshops(session)
    logger.info("Default workshop data initialization complete")


if __name__ == "__main__":
    from database.management.base import get_db_session

    # When run directly, initialize the workshops
    with get_db_session() as session:
        initialize_default_workshops(session)
