/** HTTP endpoints exclude credentials, query strings, and fragments. */
export function validEndpoint(value: string): boolean {
  try {
    const url = new URL(value.trim());
    return (
      (url.protocol === "http:" || url.protocol === "https:") &&
      !url.username &&
      !url.password &&
      !url.search &&
      !url.hash &&
      !/[?#]/.test(value)
    );
  } catch {
    return false;
  }
}

/** Remove URL userinfo before errors cross model, browser, or log boundaries. */
export function safeError(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  return message.replace(/(https?:\/\/)[^\s/]+@/gi, "$1[redacted]@");
}
