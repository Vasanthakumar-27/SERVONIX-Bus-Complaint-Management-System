/**
 * Media Handler - Graceful fallback for missing files
 * Provides placeholder images and error handling for 404 media
 */

class MediaHandler {
    constructor() {
        this.retryAttempts = 2;
        this.retryDelay = 1000; // ms
        this.placeholderImage = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2YzZjRmNiIvPjxwYXRoIGQ9Ik0xMDAgNTBsNDAgNDBoLTI1djQwaC0zMHYtNDBoLTI1eiIgZmlsbD0iI2Q1ZDhkZCIvPjx0ZXh0IHg9IjUwJSIgeT0iNzAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5Y2ExYWEiIHRleHQtYW5jaG9yPSJtaWRkbGUiPkltYWdlIG5vdCBmb3VuZDwvdGV4dD48L3N2Zz4=';
        this.placeholderFile = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZjJmZiIvPjxwYXRoIGQ9Ik04MCA1MGg0MHY4MGgtNDB6TTgwIDEzMGg0MHYyMGgtNDB6IiBmaWxsPSIjM2I4MmY2IiBvcGFjaXR5PSIwLjMiLz48dGV4dCB4PSI1MCUiIHk9Ijc1JSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjE0IiBmaWxsPSIjNjY2IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5GaWxlIG5vdCBmb3VuZDwvdGV4dD48L3N2Zz4=';
    }

    /**
     * Load image with retry and fallback
     */
    async loadImage(url, isImage = true) {
        for (let attempt = 0; attempt < this.retryAttempts; attempt++) {
            try {
                const response = await fetch(url, {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });

                if (response.ok) {
                    const blob = await response.blob();
                    return URL.createObjectURL(blob);
                }

                if (response.status === 404) {
                    console.warn(`Media file not found (404): ${url}`);
                    return isImage ? this.placeholderImage : this.placeholderFile;
                }
            } catch (error) {
                console.error(`Attempt ${attempt + 1} failed for ${url}:`, error);
                
                if (attempt < this.retryAttempts - 1) {
                    await this.delay(this.retryDelay);
                }
            }
        }

        // All attempts failed, return placeholder
        return isImage ? this.placeholderImage : this.placeholderFile;
    }

    /**
     * Create fallback image element
     */
    createFallbackImage(originalSrc, alt = 'Image not available') {
        const img = document.createElement('img');
        img.alt = alt;
        img.style.cssText = 'width: 100%; height: 100%; object-fit: cover;';
        
        // Try to load the image
        this.loadImage(originalSrc, true).then(src => {
            img.src = src;
        });

        return img;
    }

    /**
     * Handle image error with fallback
     */
    handleImageError(imgElement, isImage = true) {
        if (imgElement.dataset.fallbackApplied) {
            return; // Already applied fallback
        }

        imgElement.dataset.fallbackApplied = 'true';
        imgElement.src = isImage ? this.placeholderImage : this.placeholderFile;
        imgElement.style.objectFit = 'contain';
        imgElement.style.padding = '20px';
        
        // Add visual indicator
        const parent = imgElement.parentElement;
        if (parent && !parent.querySelector('.media-error-badge')) {
            const badge = document.createElement('div');
            badge.className = 'media-error-badge';
            badge.innerHTML = '<i class="fas fa-exclamation-triangle"></i> File not found';
            badge.style.cssText = `
                position: absolute;
                top: 8px;
                right: 8px;
                background: rgba(239, 68, 68, 0.9);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                z-index: 10;
            `;
            parent.style.position = 'relative';
            parent.appendChild(badge);
        }
    }

    /**
     * Validate media file existence
     */
    async validateMediaFile(filePath) {
        try {
            const response = await fetch(filePath, {
                method: 'HEAD',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            return response.ok;
        } catch {
            return false;
        }
    }

    /**
     * Enhanced media display with validation
     */
    displayMedia(mediaFile, container) {
        const fileUrl = mediaFile.file_path.startsWith('http') 
            ? mediaFile.file_path 
            : `${window.API_BASE || 'http://127.0.0.1:5000'}${mediaFile.file_path.startsWith('/') ? '' : '/'}${mediaFile.file_path}`;

        const isImage = mediaFile.mime_type && mediaFile.mime_type.startsWith('image/');
        
        const mediaElement = document.createElement('div');
        mediaElement.className = 'media-item';
        mediaElement.style.cssText = `
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            position: relative;
        `;

        if (mediaFile.file_exists === false) {
            // Backend already told us the file doesn't exist
            mediaElement.innerHTML = `
                <div style="width: 100%; height: 150px; display: flex; align-items: center; justify-content: center; background: #fee; flex-direction: column; gap: 8px;">
                    <i class="fas fa-exclamation-circle" style="font-size: 40px; color: #ef4444;"></i>
                    <span style="font-size: 12px; color: #dc2626;">File not found</span>
                </div>
                <div style="padding: 8px; font-size: 11px; color: var(--text-400); word-break: break-all;">
                    ${mediaFile.file_name || 'Attachment'}
                </div>
            `;
        } else if (isImage) {
            mediaElement.innerHTML = `
                <img src="${fileUrl}" 
                     alt="${mediaFile.file_name}" 
                     style="width: 100%; height: 150px; object-fit: cover; cursor: pointer;" 
                     onerror="window.mediaHandler.handleImageError(this, true)"
                     onclick="window.open('${fileUrl}', '_blank')">
                <div style="padding: 8px; font-size: 11px; color: var(--text-400); word-break: break-all;">
                    ${mediaFile.file_name || 'Image'}
                </div>
            `;
        } else {
            mediaElement.innerHTML = `
                <div style="width: 100%; height: 150px; display: flex; align-items: center; justify-content: center; background: var(--primary-soft); cursor: pointer;" 
                     onclick="window.open('${fileUrl}', '_blank')">
                    <i class="fas fa-file" style="font-size: 40px; color: var(--primary);"></i>
                </div>
                <div style="padding: 8px; font-size: 11px; color: var(--text-400); word-break: break-all;">
                    ${mediaFile.file_name || 'Attachment'}
                </div>
            `;
        }

        container.appendChild(mediaElement);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize global instance
window.mediaHandler = new MediaHandler();

// Add CSS for media error states
const mediaStyles = document.createElement('style');
mediaStyles.textContent = `
    .media-item {
        transition: transform 0.2s ease;
    }
    
    .media-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .media-error-badge {
        animation: fadeIn 0.3s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-5px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(mediaStyles);

console.log('✅ Media Handler initialized with graceful fallbacks');
