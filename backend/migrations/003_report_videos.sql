CREATE TABLE IF NOT EXISTS report_videos (
 report_id INTEGER PRIMARY KEY REFERENCES training_reports(id),
 mime TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL,
 duration_s REAL NOT NULL, preview_flipped INTEGER NOT NULL,
 chunk_count INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'uploading',
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS report_video_chunks (
 report_id INTEGER NOT NULL REFERENCES report_videos(report_id),
 chunk_index INTEGER NOT NULL, data BLOB NOT NULL,
 PRIMARY KEY(report_id,chunk_index)
);
