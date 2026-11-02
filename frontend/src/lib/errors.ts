function flatten(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(flatten).filter(Boolean).join(" ");
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => {
        const text = flatten(item);
        return text ? `${key}: ${text}` : "";
      })
      .filter(Boolean)
      .join(" ");
  }
  return "";
}

export function errorMessage(error: unknown, fallback: string) {
  const response = (error as { response?: { status?: number; data?: { detail?: string; errors?: unknown } } }).response;
  const data = response?.data;
  if (response?.status === 403) {
    return data?.detail || "You do not have permission to perform this action.";
  }
  if (data?.errors) {
    const text = flatten(data.errors);
    if (text) return text;
  }
  if (data?.detail) return data.detail;
  return fallback;
}
