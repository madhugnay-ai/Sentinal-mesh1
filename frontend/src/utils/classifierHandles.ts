export type ClassifierHandleDefinition = {
  id: string;
  label: string;
  top: string;
};

export function normalizeClassifierCategory(category?: unknown): string {
  return typeof category === 'string' ? category.trim().toLowerCase() : '';
}

export function getClassifierHandleDefinitions(categories?: string[] | null): ClassifierHandleDefinition[] {
  const normalizedCategories = (categories ?? [])
    .map((category) => normalizeClassifierCategory(category))
    .filter(Boolean);

  return normalizedCategories.map((category, index) => ({
    id: category,
    label: category,
    top: `${20 + index * 18}%`,
  }));
}
