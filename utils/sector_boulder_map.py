import pandas as pd
from utils.loggers import logger
from supabase import Client


def create_mappings_from_excel(supabase: Client, excel_path: str) -> list:
    """
    Create mappings from Excel file.

    Args:
        supabase (Client): Supabase client
        excel_path (str): Path to Excel file

    Returns:
        list: List of mappings
    """
    try:
        # Get sectors from Supabase
        response = supabase.table("sectors").select("id,name").execute()
        sectors = response.data

        # Create a mapping of sector names to IDs
        sector_name_to_id = {
            sector['name']: sector['id']
            for sector in sectors
        }

        # Read Excel file
        df = pd.read_excel(excel_path)

        # Create mappings
        mappings = []
        for _, row in df.iterrows():
            sector_name = row['sector_name']
            boulder_url = row['boulder_url']

            sector_id = sector_name_to_id.get(sector_name)
            if not sector_id:
                logger.warning(f"No sector found for name: {sector_name}")
                continue

            mappings.append({
                'sector_id': sector_id,
                'boulder_url': boulder_url
            })

        return mappings

    except Exception as e:
        logger.error(f"Error creating mappings from Excel: {str(e)}")
        return []
