CREATE TABLE IF NOT EXISTS patient_training_selection (
 patient_id INTEGER PRIMARY KEY REFERENCES patients(id),
 condition TEXT,
 exercise_ids_json TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
