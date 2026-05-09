export type GradeBookComponent = {
  id: string;
  name: string;
  weight_percent: number;
  score_percent: number | null;
};

export type LetterCutoff = { letter: string; min_percent: number };

/** Contribution to course % when weights sum to 100. Ungraded rows contribute 0. */
export function coursePercentEarned(components: GradeBookComponent[]): number {
  return components.reduce((sum, c) => {
    if (c.score_percent == null) return sum;
    return sum + (c.weight_percent * c.score_percent) / 100;
  }, 0);
}

export function remainingWeightPercent(components: GradeBookComponent[]): number {
  return components
    .filter((c) => c.score_percent == null)
    .reduce((s, c) => s + c.weight_percent, 0);
}

export function maxPossibleCoursePercent(components: GradeBookComponent[]): number {
  return coursePercentEarned(components) + remainingWeightPercent(components);
}

/** Average % needed on all remaining (ungraded) weight to hit `target` course %. */
export function requiredAverageOnRemaining(
  components: GradeBookComponent[],
  target: number
): number | null {
  const earned = coursePercentEarned(components);
  const rem = remainingWeightPercent(components);
  if (rem < 1e-6) return null;
  return ((target - earned) / rem) * 100;
}

export function letterForPercent(
  pct: number,
  cutoffs: LetterCutoff[],
  fallback = 'F'
): string {
  const sorted = [...cutoffs].sort((a, b) => b.min_percent - a.min_percent);
  for (const row of sorted) {
    if (pct >= row.min_percent) return row.letter.toUpperCase();
  }
  return fallback;
}

export function weightsSum(components: GradeBookComponent[]): number {
  return components.reduce((s, c) => s + c.weight_percent, 0);
}
