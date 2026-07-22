export const config = {
  apiBase: (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000").replace(/\/$/, ""),
  useMock: (process.env.NEXT_PUBLIC_USE_MOCK ?? "true") !== "false",
};
