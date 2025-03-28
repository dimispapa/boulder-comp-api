import pandas as pd
from utils.loggers import logger
from supabase import Client


def create_mappings_from_excel(supabase: Client,
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

        # Prepare all mappings in one batch
        mapping_data = []
        skipped_count = 0

        for _, row in df.iterrows():
            boulder_url = row['boulder_url']
            sector_name = row['sector_name']

            # Find the sector ID for this name
            sector_id = sector_name_to_id.get(sector_name)
            if not sector_id:
                logger.warning(f"No sector found with name: {sector_name}")
                skipped_count += 1
                continue

            # Add to batch
            mapping_data.append({
                'boulder_url': boulder_url,
                'sector_id': sector_id
            })

        # If we have mappings to insert
        if mapping_data:
            try:
                # Get a connection from the pool and start a transaction
                conn = supabase.pool.acquire()
                conn.transaction()

                # Use upsert with on_conflict parameter to handle duplicates
                result = conn.table('boulder_sector_mappings').upsert(
                    mapping_data,
                    on_conflict='boulder_url'
                ).execute()

                # If we got here without errors, commit the transaction
                conn.commit()

                logger.info(
                    f"Successfully upserted {len(mapping_data)} "
                    f"boulder-sector mappings (skipped {skipped_count})")
                return result.data

            except Exception as e:
                # Rollback transaction on error
                conn.rollback()
                logger.error(f"Transaction error: {str(e)}, rolling back")
                raise
            finally:
                # Always release the connection back to the pool
                supabase.pool.release(conn)
        else:
            logger.warning(
                f"No valid mappings found to insert (skipped {skipped_count})")
            return []

    except Exception as e:
        logger.error(f"Error creating mappings from Excel: {str(e)}")
        raise
