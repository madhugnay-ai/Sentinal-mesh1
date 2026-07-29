export type ClassifierHandleDefinition = {
  id: string;
  label: string;
  top: string;
};

export function getClassifierHandleDefinitions(categories?: string[] | null): ClassifierHandleDefinition[] {
  const normalizedCategories = (categories ?? [])
    .map((category) => (typeof category === 'string' ? category.trim() : ''))
    .filter(Boolean);

  return normalizedCategories.map((category, index) => ({
    id: category,
    label: category,
    top: `${20 + index * 18}%`,
  }));
}
