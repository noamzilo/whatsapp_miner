#!/usr/bin/env python3
"""
Database Migration Script

This script handles database migration between different environments (dev, prd, etc.)
It dumps the destination database first, then copies data from source to destination,
and finally runs migrations on the destination database.

Usage:
    python db_migrate.py --src dev --dst prd
    python db_migrate.py --src dev_personal --dst prd
"""

import argparse
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles database migration operations between environments."""
    
    def __init__(self, project: str = "whatsapp_miner_backend"):
        """
        Initialize the database migrator.
        
        Args:
            project: The doppler project name
        """
        self.project = project
        
    def get_db_url(self, config: str) -> str:
        """
        Get database URL from doppler for the specified config.
        
        Args:
            config: The doppler config name (e.g., 'dev', 'prd', 'dev_personal')
            
        Returns:
            The database connection string
            
        Raises:
            subprocess.CalledProcessError: If doppler command fails
        """
        logger.info(f"Getting database URL for config: {config}")
        
        cmd = [
            "doppler", "run", 
            "--project", self.project, 
            "--config", config, 
            "--", "bash", "-c", 
            'echo "$SUPABASE_DATABASE_CONNECTION_STRING"'
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        db_url = result.stdout.strip()
        if not db_url:
            raise ValueError(f"Empty database URL returned for config: {config}")
            
        logger.info(f"Successfully retrieved database URL for {config}")
        return db_url
    
    def dump_database(self, db_url: str, dump_dir: Path) -> None:
        """
        Dump the database using Supabase CLI.
        
        Args:
            db_url: Database connection string
            dump_dir: Directory to save the dump files
            
        Raises:
            subprocess.CalledProcessError: If dump fails
        """
        logger.info(f"Dumping database to: {dump_dir}")
        
        # Create dump directory
        dump_dir.mkdir(parents=True, exist_ok=True)
        
        # Dump roles
        roles_file = dump_dir / "roles.sql"
        roles_cmd = ["supabase", "db", "dump", "--db-url", db_url, "-f", str(roles_file), "--role-only"]
        subprocess.run(roles_cmd, check=True)
        logger.info(f"Roles dumped to: {roles_file}")
        
        # Dump schema
        schema_file = dump_dir / "schema.sql"
        schema_cmd = ["supabase", "db", "dump", "--db-url", db_url, "-f", str(schema_file)]
        subprocess.run(schema_cmd, check=True)
        logger.info(f"Schema dumped to: {schema_file}")
        
        # Dump data
        data_file = dump_dir / "data.sql"
        data_cmd = ["supabase", "db", "dump", "--db-url", db_url, "-f", str(data_file), "--use-copy", "--data-only"]
        subprocess.run(data_cmd, check=True)
        logger.info(f"Data dumped to: {data_file}")
        
        logger.info(f"Database dump completed: {dump_dir}")
    
    def restore_database(self, db_url: str, dump_dir: Path) -> None:
        """
        Restore database using Supabase CLI approach.
        
        Args:
            db_url: Database connection string
            dump_dir: Directory containing the dump files
            
        Raises:
            subprocess.CalledProcessError: If restore fails
        """
        logger.info(f"Restoring database from: {dump_dir}")
        
        roles_file = dump_dir / "roles.sql"
        schema_file = dump_dir / "schema.sql"
        data_file = dump_dir / "data.sql"
        
        # Restore using psql with the Supabase CLI approach
        cmd = [
            "psql",
            "--single-transaction",
            "--variable", "ON_ERROR_STOP=1",
            "--file", str(roles_file),
            "--file", str(schema_file),
            "--command", "SET session_replication_role = replica",
            "--file", str(data_file),
            "--dbname", db_url
        ]
        
        subprocess.run(cmd, check=True)
        logger.info("Database restore completed")
    
    def run_migrations(self, config: str) -> None:
        """
        Run alembic migrations on the specified config.
        
        Args:
            config: The doppler config name
            
        Raises:
            subprocess.CalledProcessError: If migration fails
        """
        logger.info(f"Running migrations on config: {config}")
        
        # Run alembic migrations
        cmd = [
            "doppler", "run",
            "--project", self.project,
            "--config", config,
            "--", "poetry", "run", "alembic", "upgrade", "head"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info("Migrations completed successfully")
    
    def clear_database_completely(self, db_url: str) -> None:
        """
        Clear all data from the database by truncating all tables and resetting sequences.
        This is compatible with Supabase where we can't drop/recreate databases.
        
        Args:
            db_url: Database connection string
            
        Raises:
            subprocess.CalledProcessError: If operation fails
        """
        logger.info("Clearing database completely")
        
        # Extract database name from URL
        # URL format: postgresql://user:pass@host:port/dbname
        # Handle URLs with query parameters
        db_name = db_url.split('/')[-1].split('?')[0]
        logger.info(f"Database name extracted: {db_name}")
        
        # For Supabase, we can't drop the database directly
        # Instead, we'll truncate all tables and sequences
        logger.info("Using truncate approach for Supabase compatibility")
        
        # Connect to the database and drop all tables
        drop_cmd = [
            "psql", db_url,
            "-c", """
            DO $$ 
            DECLARE 
                r RECORD;
            BEGIN
                -- Disable foreign key checks temporarily
                SET session_replication_role = replica;
                
                -- Drop all tables in the correct order (foreign keys first)
                FOR r IN (
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public' 
                    ORDER BY tablename
                ) LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
                
                -- Drop all sequences
                FOR r IN (
                    SELECT sequence_name 
                    FROM information_schema.sequences 
                    WHERE sequence_schema = 'public'
                ) LOOP
                    EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequence_name) || ' CASCADE';
                END LOOP;
                
                -- Re-enable foreign key checks
                SET session_replication_role = DEFAULT;
            END $$;
            """
        ]
        
        subprocess.run(drop_cmd, check=True)
        logger.info("Database cleared successfully (all tables and sequences dropped)")
        
        # Ensure public schema exists and is set as default
        schema_cmd = [
            "psql", db_url,
            "-c", """
            CREATE SCHEMA IF NOT EXISTS public;
            SET search_path TO public;
            GRANT ALL ON SCHEMA public TO postgres;
            GRANT ALL ON SCHEMA public TO public;
            """
        ]
        
        subprocess.run(schema_cmd, check=True)
        logger.info("Ensured public schema is properly configured")
    
    def migrate(self, src_config: str, dst_config: str, backup_dst: bool = True, clear_dst: bool = False) -> None:
        """
        Perform complete database migration from source to destination.
        
        Args:
            src_config: Source doppler config (e.g., 'dev', 'dev_personal')
            dst_config: Destination doppler config (e.g., 'prd')
            backup_dst: Whether to backup destination before migration
            clear_dst: Whether to clear destination database before migration
            
        Raises:
            subprocess.CalledProcessError: If any step fails
            ValueError: If invalid arguments provided
        """
        if src_config == dst_config:
            raise ValueError("Source and destination configs cannot be the same")
        
        logger.info(f"Starting migration from {src_config} to {dst_config}")
        
        try:
            # Step 1: Get database URLs
            src_db_url = self.get_db_url(src_config)
            dst_db_url = self.get_db_url(dst_config)
            
            # Step 2: Backup destination if requested
            if backup_dst:
                backup_dir = Path(tempfile.mkdtemp(prefix=f'{dst_config}_backup_'))
                logger.info(f"Creating backup of {dst_config} database")
                self.dump_database(dst_db_url, backup_dir)
                logger.info(f"Backup created: {backup_dir}")
            
            # Step 3: Clear destination if requested
            if clear_dst:
                logger.info(f"Clearing {dst_config} database completely")
                self.clear_database_completely(dst_db_url)
            
            # Step 4: Dump source database
            dump_dir = Path(tempfile.mkdtemp(prefix=f'{src_config}_dump_'))
            logger.info(f"Dumping {src_config} database")
            self.dump_database(src_db_url, dump_dir)
            
            # Step 5: Restore to destination
            logger.info(f"Restoring {src_config} data to {dst_config}")
            self.restore_database(dst_db_url, dump_dir)
            
            # Step 6: Run migrations on destination
            logger.info(f"Running migrations on {dst_config}")
            self.run_migrations(dst_config)
            
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            # Cleanup temporary directories
            if 'backup_dir' in locals():
                import shutil
                shutil.rmtree(backup_dir, ignore_errors=True)
                logger.info(f"Cleaned up backup directory: {backup_dir}")
            if 'dump_dir' in locals():
                import shutil
                shutil.rmtree(dump_dir, ignore_errors=True)
                logger.info(f"Cleaned up dump directory: {dump_dir}")


def main() -> None:
    """Main entry point for the database migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate database between different environments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python db_migrate.py --src dev --dst prd
  python db_migrate.py --src dev_personal --dst prd
  python db_migrate.py --src dev --dst prd --no-backup
  python db_migrate.py --src dev --dst prd --clear
        """
    )
    
    parser.add_argument(
        "--src",
        required=True,
        help="Source doppler config (e.g., 'dev', 'dev_personal')"
    )
    
    parser.add_argument(
        "--dst", 
        required=True,
        help="Destination doppler config (e.g., 'prd')"
    )
    
    parser.add_argument(
        "--project",
        default="whatsapp_miner_backend",
        help="Doppler project name (default: whatsapp_miner_backend)"
    )
    
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backing up destination database before migration (use with caution)"
    )
    
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Drop all tables in destination database before migration (use with caution)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if args.src == args.dst:
        logger.error("Source and destination configs cannot be the same")
        sys.exit(1)
    
    try:
        migrator = DatabaseMigrator(project=args.project)
        migrator.migrate(
            src_config=args.src,
            dst_config=args.dst,
            backup_dst=not args.no_backup,
            clear_dst=args.clear
        )
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {e}")
        if e.stdout:
            logger.error(f"stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"stderr: {e.stderr}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 