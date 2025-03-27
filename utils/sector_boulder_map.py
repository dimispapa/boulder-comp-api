import pandas as pd
from utils.loggers import logger
from supabase import Client


async def create_mappings_from_excel(supabase: Client,
                                     excel_path: str) -> list[dict]:
    """
    Create boulder-sector mappings in database from an Excel file.

    Args:
        supabase (Client): Supabase client
        excel_path (str): Path to the Excel file with boulder_url
        and sector columns
    """
    try:

        # Read the Excel file
        df = pd.read_excel(excel_path)

        # Get current sectors from database
        sectors_result = supabase.table('sectors').select('id',
                                                          'name').execute()
        sector_name_to_id = {
            sector['name']: sector['id']
            for sector in sectors_result.data
        }

        # Process each row in the Excel file
        for _, row in df.iterrows():
            boulder_url = row['boulder_url']
            sector_name = row['sector_name']

            # Find the sector ID for this name
            sector_id = sector_name_to_id.get(sector_name)
            if not sector_id:
                logger.warning(f"No sector found with name: {sector_name}")
                continue

            # Insert the mapping
            mapping_data = {'boulder_url': boulder_url, 'sector_id': sector_id}

            # Use upsert to handle duplicates
            result = await supabase.table('boulder_sector_mappings').upsert(
                mapping_data).execute()
            logger.info(f"Upserted mapping for {boulder_url} -> {sector_name}")

        logger.info(f"Successfully created mappings from Excel: {excel_path}")
        return result.data

    except Exception as e:
        logger.error(f"Error creating mappings from Excel: {str(e)}")
        raise
