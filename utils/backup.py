"""
Brewery Manager - Backup Utility
Database backup and restore functionality
"""

import os
import shutil
import sqlite3
import json
import gzip
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional


class BackupManager:
    """Manages database backups and restores"""
    
    def __init__(self, db_path: str, backup_dir: str = None):
        """
        Initialize backup manager
        
        Args:
            db_path: Path to the SQLite database file
            backup_dir: Directory to store backups (default: brewery_manager/backups)
        """
        self.db_path = db_path
        
        if backup_dir is None:
            # Default to backups directory relative to the database
            base_dir = os.path.dirname(os.path.dirname(db_path))
            backup_dir = os.path.join(base_dir, 'backups')
        
        self.backup_dir = backup_dir
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """Ensure backup directory exists"""
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self, compress: bool = True, include_timestamp: bool = True) -> Dict:
        """
        Create a backup of the database
        
        Args:
            compress: Whether to compress the backup with gzip
            include_timestamp: Whether to include timestamp in filename
        
        Returns:
            Dict with backup information
        """
        try:
            # Generate backup filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if include_timestamp:
                backup_name = f"brewery_backup_{timestamp}.db"
            else:
                backup_name = "brewery_backup.db"
            
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Create backup using SQLite's backup API (safer than file copy)
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(backup_path)
            
            with backup_conn:
                source_conn.backup(backup_conn)
            
            backup_conn.close()
            source_conn.close()
            
            # Get backup size
            backup_size = os.path.getsize(backup_path)
            
            # Compress if requested
            if compress:
                compressed_path = f"{backup_path}.gz"
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove uncompressed file
                os.remove(backup_path)
                backup_path = compressed_path
                backup_size = os.path.getsize(backup_path)
            
            # Get database stats
            stats = self._get_db_stats()
            
            return {
                'success': True,
                'backup_path': backup_path,
                'backup_name': os.path.basename(backup_path),
                'backup_size': backup_size,
                'backup_size_mb': round(backup_size / (1024 * 1024), 2),
                'timestamp': timestamp,
                'compressed': compress,
                'stats': stats
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def restore_backup(self, backup_filename: str) -> Dict:
        """
        Restore database from a backup
        
        Args:
            backup_filename: Name of the backup file to restore
        
        Returns:
            Dict with restore information
        """
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            if not os.path.exists(backup_path):
                return {
                    'success': False,
                    'error': f'Backup file not found: {backup_filename}'
                }
            
            # Check if compressed
            is_compressed = backup_path.endswith('.gz')
            
            # Create a temporary file for decompression if needed
            if is_compressed:
                temp_path = backup_path[:-3]  # Remove .gz extension
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                restore_from = temp_path
            else:
                restore_from = backup_path
            
            # Create a backup of current database before restore
            current_backup = self.create_backup(compress=True, include_timestamp=True)
            
            # Restore the database
            # Close any existing connections first (this should be handled by the app)
            # For safety, we'll copy the backup over the current database
            shutil.copy2(restore_from, self.db_path)
            
            # Clean up temp file if we decompressed
            if is_compressed:
                os.remove(temp_path)
            
            # Get stats of restored database
            stats = self._get_db_stats()
            
            return {
                'success': True,
                'restored_from': backup_filename,
                'pre_restore_backup': current_backup.get('backup_name'),
                'stats': stats
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_backups(self) -> List[Dict]:
        """
        List all available backups
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        try:
            for filename in sorted(os.listdir(self.backup_dir), reverse=True):
                if filename.startswith('brewery_backup_'):
                    filepath = os.path.join(self.backup_dir, filename)
                    stat = os.stat(filepath)
                    
                    backups.append({
                        'filename': filename,
                        'path': filepath,
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'compressed': filename.endswith('.gz')
                    })
        
        except Exception as e:
            print(f"Error listing backups: {e}")
        
        return backups
    
    def delete_backup(self, backup_filename: str) -> Dict:
        """
        Delete a backup file
        
        Args:
            backup_filename: Name of the backup file to delete
        
        Returns:
            Dict with deletion status
        """
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            if not os.path.exists(backup_path):
                return {
                    'success': False,
                    'error': f'Backup file not found: {backup_filename}'
                }
            
            # Safety check - don't delete if it's not in the backup directory
            if not backup_path.startswith(self.backup_dir):
                return {
                    'success': False,
                    'error': 'Invalid backup path'
                }
            
            os.remove(backup_path)
            
            return {
                'success': True,
                'deleted': backup_filename
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_old_backups(self, keep_count: int = 10) -> Dict:
        """
        Delete old backups, keeping only the specified number of recent backups
        
        Args:
            keep_count: Number of recent backups to keep
        
        Returns:
            Dict with cleanup information
        """
        try:
            backups = self.list_backups()
            
            if len(backups) <= keep_count:
                return {
                    'success': True,
                    'deleted_count': 0,
                    'kept_count': len(backups)
                }
            
            # Delete oldest backups
            to_delete = backups[keep_count:]
            deleted = []
            
            for backup in to_delete:
                result = self.delete_backup(backup['filename'])
                if result['success']:
                    deleted.append(backup['filename'])
            
            return {
                'success': True,
                'deleted_count': len(deleted),
                'deleted_files': deleted,
                'kept_count': keep_count
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_to_json(self, include_timestamp: bool = True) -> Dict:
        """
        Export database to JSON format
        
        Args:
            include_timestamp: Whether to include timestamp in filename
        
        Returns:
            Dict with export information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row['name'] for row in cursor.fetchall()]
            
            # Export each table
            export_data = {
                'export_date': datetime.now().isoformat(),
                'tables': {}
            }
            
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                export_data['tables'][table] = [dict(row) for row in rows]
            
            conn.close()
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if include_timestamp:
                export_name = f"brewery_export_{timestamp}.json"
            else:
                export_name = "brewery_export.json"
            
            export_path = os.path.join(self.backup_dir, export_name)
            
            # Write JSON file
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str, ensure_ascii=False)
            
            # Compress the JSON file
            compressed_path = f"{export_path}.gz"
            with open(export_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            os.remove(export_path)
            
            export_size = os.path.getsize(compressed_path)
            
            return {
                'success': True,
                'export_path': compressed_path,
                'export_name': os.path.basename(compressed_path),
                'export_size': export_size,
                'export_size_mb': round(export_size / (1024 * 1024), 2),
                'tables_exported': len(tables),
                'table_names': tables
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_db_stats(self) -> Dict:
        """Get database statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get table counts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            table_counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = cursor.fetchone()[0]
            
            # Get database size
            db_size = os.path.getsize(self.db_path)
            
            conn.close()
            
            return {
                'total_tables': len(tables),
                'table_counts': table_counts,
                'db_size': db_size,
                'db_size_mb': round(db_size / (1024 * 1024), 2)
            }
        
        except Exception as e:
            return {
                'error': str(e)
            }
    
    def get_backup_info(self) -> Dict:
        """Get backup directory information"""
        backups = self.list_backups()
        
        total_size = sum(b['size'] for b in backups)
        
        return {
            'backup_dir': self.backup_dir,
            'backup_count': len(backups),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'backups': backups
        }


def get_backup_manager(db_path: str = None) -> BackupManager:
    """
    Get a BackupManager instance
    
    Args:
        db_path: Path to database (default: brewery_manager/data/brewery.db)
    
    Returns:
        BackupManager instance
    """
    if db_path is None:
        # Default database path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, 'data', 'brewery.db')
    
    return BackupManager(db_path)