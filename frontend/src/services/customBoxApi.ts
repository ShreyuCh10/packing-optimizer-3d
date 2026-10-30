import type {CustomBoxRequest, CustomBoxResult} from "../types/customBox";

const API_URL ="http://localhost:8000";

export async function createCustomBoxModel(
  request: CustomBoxRequest
): Promise<string> {
  const response = await fetch(`${API_URL}/custom-box/model`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Model request failed with status ${response.status}`);
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob); // a temporary URL the viewer can load
}