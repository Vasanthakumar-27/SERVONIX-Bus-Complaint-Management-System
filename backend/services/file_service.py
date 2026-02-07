"""File upload and validation service"""
import os
import logging
from werkzeug.utils import secure_filename
from datetime import datetime
import mimetypes

logger = logging.getLogger(__name__)


class FileService:
    """Handles file uploads, validation, and storage"""
    
    # Allowed file extensions by category
    ALLOWED_EXTENSIONS = {
        'images': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'},
        'videos': {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'},
        'documents': {'pdf', 'doc', 'docx', 'txt', 'rtf'},
        'all': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'mp4', 'avi', 'mov', 
                'mkv', 'wmv', 'flv', 'webm', 'pdf', 'doc', 'docx', 'txt', 'rtf'}
    }
    
    # Maximum file sizes (in bytes)
    MAX_SIZES = {
        'image': 10 * 1024 * 1024,      # 10MB for images
        'video': 100 * 1024 * 1024,     # 100MB for videos
        'document': 20 * 1024 * 1024,   # 20MB for documents
        'default': 1024 * 1024 * 1024   # 1GB default
    }
    
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)
        logger.info(f"FileService initialized with upload folder: {upload_folder}")
    
    def _get_file_category(self, extension):
        """Determine file category based on extension"""
        extension = extension.lower()
        if extension in self.ALLOWED_EXTENSIONS['images']:
            return 'image'
        elif extension in self.ALLOWED_EXTENSIONS['videos']:
            return 'video'
        elif extension in self.ALLOWED_EXTENSIONS['documents']:
            return 'document'
        return 'unknown'
    
    def is_allowed_file(self, filename, allowed_categories=None):
        """
        Check if file extension is allowed
        
        Args:
            filename: Name of the file
            allowed_categories: List of allowed categories ['images', 'videos', 'documents'] 
                               or None for all
        
        Returns:
            bool: True if file extension is allowed
        """
        if not filename or '.' not in filename:
            return False
        
        extension = filename.rsplit('.', 1)[1].lower()
        
        if allowed_categories is None:
            # Allow all supported extensions
            return extension in self.ALLOWED_EXTENSIONS['all']
        
        # Check against specific categories
        allowed_exts = set()
        for category in allowed_categories:
            if category in self.ALLOWED_EXTENSIONS:
                allowed_exts.update(self.ALLOWED_EXTENSIONS[category])
        
        return extension in allowed_exts
    
    def validate_file_size(self, file, max_size=None):
        """
        Validate file size
        
        Args:
            file: FileStorage object from Flask request
            max_size: Maximum size in bytes, or None to use category-based limits
        
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        try:
            # Get file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset file pointer
            
            # Determine max size
            if max_size is None:
                # Use category-based limit
                extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                category = self._get_file_category(extension)
                max_size = self.MAX_SIZES.get(category, self.MAX_SIZES['default'])
            
            if file_size > max_size:
                max_mb = max_size / (1024 * 1024)
                actual_mb = file_size / (1024 * 1024)
                return False, f"File size ({actual_mb:.1f}MB) exceeds maximum allowed ({max_mb:.1f}MB)"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating file size: {e}")
            return False, "Failed to validate file size"
    
    def save_file(self, file, subfolder=None, custom_filename=None):
        """
        Save uploaded file to disk
        
        Args:
            file: FileStorage object from Flask request
            subfolder: Optional subfolder within upload_folder
            custom_filename: Optional custom filename (will be secured)
        
        Returns:
            tuple: (success: bool, file_path: str or error_message: str)
        """
        try:
            # Validate filename
            if not file or not file.filename:
                return False, "No file provided"
            
            # Secure the filename
            if custom_filename:
                # Preserve original extension
                original_ext = file.filename.rsplit('.', 1)[1] if '.' in file.filename else ''
                if '.' not in custom_filename and original_ext:
                    custom_filename = f"{custom_filename}.{original_ext}"
                filename = secure_filename(custom_filename)
            else:
                filename = secure_filename(file.filename)
            
            # Generate unique filename if file exists
            base_name, extension = os.path.splitext(filename)
            save_folder = os.path.join(self.upload_folder, subfolder) if subfolder else self.upload_folder
            os.makedirs(save_folder, exist_ok=True)
            
            file_path = os.path.join(save_folder, filename)
            counter = 1
            while os.path.exists(file_path):
                filename = f"{base_name}_{counter}{extension}"
                file_path = os.path.join(save_folder, filename)
                counter += 1
            
            # Save file
            file.save(file_path)
            logger.info(f"File saved: {file_path}")
            
            # Return relative path from upload_folder
            if subfolder:
                relative_path = os.path.join(subfolder, filename)
            else:
                relative_path = filename
            
            return True, relative_path.replace('\\', '/')  # Normalize path separators
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return False, f"Failed to save file: {str(e)}"
    
    def upload_file(self, file, allowed_categories=None, subfolder=None, max_size=None):
        """
        Complete file upload workflow: validate and save
        
        Args:
            file: FileStorage object from Flask request
            allowed_categories: List of allowed categories or None for all
            subfolder: Optional subfolder within upload_folder
            max_size: Maximum file size in bytes
        
        Returns:
            dict: {
                'success': bool,
                'file_path': str (if success),
                'error': str (if not success),
                'file_info': dict (if success)
            }
        """
        # Validate file extension
        if not self.is_allowed_file(file.filename, allowed_categories):
            categories_str = ', '.join(allowed_categories) if allowed_categories else 'all supported types'
            return {
                'success': False,
                'error': f'File type not allowed. Allowed types: {categories_str}'
            }
        
        # Validate file size
        is_valid, error_msg = self.validate_file_size(file, max_size)
        if not is_valid:
            return {'success': False, 'error': error_msg}
        
        # Save file
        success, result = self.save_file(file, subfolder)
        if not success:
            return {'success': False, 'error': result}
        
        # Get file info
        file_path = result
        extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        category = self._get_file_category(extension)
        
        return {
            'success': True,
            'file_path': file_path,
            'file_info': {
                'original_filename': file.filename,
                'saved_filename': os.path.basename(file_path),
                'extension': extension,
                'category': category,
                'mime_type': mimetypes.guess_type(file.filename)[0],
                'uploaded_at': datetime.now().isoformat()
            }
        }
    
    def delete_file(self, file_path):
        """
        Delete a file from storage
        
        Args:
            file_path: Relative path from upload_folder
        
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            full_path = os.path.join(self.upload_folder, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"File deleted: {full_path}")
                return True, None
            else:
                return False, "File not found"
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False, str(e)
    
    def get_file_info(self, file_path):
        """
        Get information about a stored file
        
        Args:
            file_path: Relative path from upload_folder
        
        Returns:
            dict or None: File information or None if not found
        """
        try:
            full_path = os.path.join(self.upload_folder, file_path)
            if not os.path.exists(full_path):
                return None
            
            stat_info = os.stat(full_path)
            extension = file_path.rsplit('.', 1)[1].lower() if '.' in file_path else ''
            
            return {
                'file_path': file_path,
                'filename': os.path.basename(file_path),
                'extension': extension,
                'category': self._get_file_category(extension),
                'size_bytes': stat_info.st_size,
                'size_mb': stat_info.st_size / (1024 * 1024),
                'created_at': datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                'mime_type': mimetypes.guess_type(file_path)[0]
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None


def create_file_service(upload_folder):
    """Factory function to create FileService instance"""
    return FileService(upload_folder)
