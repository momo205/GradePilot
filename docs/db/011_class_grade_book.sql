-- Persist syllabus-style weighted grade breakdown and entered scores per class.
ALTER TABLE classes
  ADD COLUMN IF NOT EXISTS grade_book JSONB DEFAULT NULL;

COMMENT ON COLUMN classes.grade_book IS
  'Weighted components (name, weight_percent, score_percent), pass_percent, target_percent, optional letter_cutoffs';
