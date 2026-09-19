CREATE TABLE IF NOT EXISTS training_reports (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 patient_id INTEGER NOT NULL REFERENCES patients(id),
 client_id TEXT NOT NULL,
 exercise_id TEXT NOT NULL,
 result_json TEXT NOT NULL,
 created_at TEXT NOT NULL,
 read_by INTEGER REFERENCES users(id),
 read_at TEXT,
 UNIQUE(patient_id, client_id)
);
CREATE INDEX IF NOT EXISTS idx_training_reports_patient ON training_reports(patient_id,id DESC);
