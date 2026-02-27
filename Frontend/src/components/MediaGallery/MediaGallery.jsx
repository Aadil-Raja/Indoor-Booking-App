import { useState, useEffect } from 'react';
import { mediaService } from '../../services/mediaService';
import './mediaGallery.css';

const MediaGallery = ({ type, id, onMediaUpdate }) => {
  // type: 'property' or 'court'
  // id: propertyId or courtId
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [caption, setCaption] = useState('');
  const [mediaType, setMediaType] = useState('image');

  useEffect(() => {
    fetchMedia();
  }, [type, id]);

  const fetchMedia = async () => {
    try {
      setLoading(true);
      setError('');
      const result =
        type === 'property'
          ? await mediaService.getPropertyMedia(id)
          : await mediaService.getCourtMedia(id);

      if (result.success) {
        setMedia(result.data || []);
        if (onMediaUpdate) onMediaUpdate(result.data || []);
      }
    } catch (err) {
      setError('Failed to load media');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const validImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    const validVideoTypes = ['video/mp4', 'video/webm', 'video/ogg'];

    if (![...validImageTypes, ...validVideoTypes].includes(file.type)) {
      setError('Please select a valid image or video file');
      return;
    }

    // Auto-detect media type
    const detectedType = validImageTypes.includes(file.type) ? 'image' : 'video';
    setMediaType(detectedType);

    setSelectedFile(file);
    setError('');

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError('');

    try {
      const result =
        type === 'property'
          ? await mediaService.uploadPropertyMedia(
              id,
              selectedFile,
              mediaType,
              caption,
              media.length
            )
          : await mediaService.uploadCourtMedia(
              id,
              selectedFile,
              mediaType,
              caption,
              media.length
            );

      if (result.success) {
        setSelectedFile(null);
        setPreview(null);
        setCaption('');
        fetchMedia();
      } else {
        setError(result.message || 'Upload failed');
      }
    } catch (err) {
      console.error('Upload error:', err);
      const errorMsg = err.response?.data?.detail || err.response?.data?.message || err.message || 'Upload failed';
      setError(errorMsg);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (mediaId) => {
    if (!window.confirm('Are you sure you want to delete this media?')) return;

    try {
      const result = await mediaService.deleteMedia(mediaId);
      if (result.success) {
        fetchMedia();
      } else {
        alert(result.message || 'Delete failed');
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Delete failed');
    }
  };

  const cancelUpload = () => {
    setSelectedFile(null);
    setPreview(null);
    setCaption('');
    setError('');
  };

  if (loading) {
    return <div className="ib-media-loading">Loading media...</div>;
  }

  return (
    <div className="ib-media-gallery">
      {/* Context Info */}
      <div className="ib-media-context-info">
        <p>
          Uploading media for: <strong>{type === 'property' ? 'Property' : 'Court'}</strong>
        </p>
      </div>

      {/* Upload Section */}
      <div className="ib-media-upload-section">
        <h3>Upload Media</h3>
        {error && <div className="ib-media-error">{error}</div>}

        {!selectedFile ? (
          <div className="ib-media-upload-area">
            <input
              type="file"
              id="media-upload"
              accept="image/*,video/*"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <label htmlFor="media-upload" className="ib-media-upload-label">
              <div className="ib-upload-icon">📁</div>
              <div className="ib-upload-text">
                <p>Click to upload image or video</p>
                <p className="ib-upload-hint">
                  Supports: JPG, PNG, GIF, WebP, MP4, WebM
                </p>
              </div>
            </label>
          </div>
        ) : (
          <div className="ib-media-preview-section">
            <div className="ib-media-preview">
              {mediaType === 'image' ? (
                <img src={preview} alt="Preview" />
              ) : (
                <video src={preview} controls />
              )}
            </div>
            <div className="ib-media-upload-form">
              <input
                type="text"
                placeholder="Add a caption (optional)"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                className="ib-media-caption-input"
              />
              <div className="ib-media-upload-actions">
                <button
                  onClick={cancelUpload}
                  className="ib-btn-secondary"
                  disabled={uploading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  className="ib-btn-primary"
                  disabled={uploading}
                >
                  {uploading ? 'Uploading...' : 'Upload'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Gallery Section */}
      <div className="ib-media-gallery-section">
        <h3>Media Gallery ({media.length})</h3>
        {media.length === 0 ? (
          <div className="ib-media-empty">
            <p>No media uploaded yet</p>
          </div>
        ) : (
          <div className="ib-media-grid">
            {media.map((item) => (
              <div key={item.id} className="ib-media-item">
                {item.media_type === 'image' ? (
                  <img
                    src={item.thumbnail_url || item.url}
                    alt={item.caption || 'Media'}
                    className="ib-media-thumbnail"
                  />
                ) : (
                  <div className="ib-media-video-thumbnail">
                    <video src={item.url} />
                    <div className="ib-video-overlay">▶</div>
                  </div>
                )}
                {item.caption && (
                  <div className="ib-media-caption">{item.caption}</div>
                )}
                <button
                  onClick={() => handleDelete(item.id)}
                  className="ib-media-delete-btn"
                  title="Delete"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MediaGallery;
