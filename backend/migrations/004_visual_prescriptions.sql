CREATE TABLE IF NOT EXISTS visual_prescriptions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 patient_id INTEGER NOT NULL REFERENCES patients(id),
 therapist_id INTEGER NOT NULL REFERENCES users(id),
 status TEXT NOT NULL CHECK(status IN ('draft','published')),
 body_json TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_visual_plan_patient ON visual_prescriptions(patient_id,therapist_id,status,id);
