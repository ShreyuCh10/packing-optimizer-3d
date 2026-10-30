import { useState } from "react";
import { createCustomBoxModel } from "../services/customBoxApi";
import type { CustomBoxResult } from "../types/customBox";

type FieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
};

// Small reusable input so we don't repeat the same markup five times
function Field({ label, value, onChange }: FieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        min="0"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
      />
    </label>
  );
}

export default function CustomBoxPanel() {
  // Inputs are kept as strings while typing, converted to numbers on submit
  const [length, setLength] = useState("2000");
  const [width, setWidth] = useState("900");
  const [height, setHeight] = useState("40");
  const [weight, setWeight] = useState("25");
  const [quantity, setQuantity] = useState("1");
  const [padding, setPadding] = useState("20");

  const [result, setResult] = useState<CustomBoxResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); // stop the browser from reloading the page
    setError(null);
    setResult(null);

    const l = Number(length);
    const w = Number(width);
    const h = Number(height);
    const wt = Number(weight);
    const q = Number(quantity);
    const p = Number(padding);

    // Mirror the backend rules so the user gets instant feedback
    if (l <= 0 || w <= 0 || h <= 0) {
      setError("Length, width and height must be greater than 0.");
      return;
    }
    if (wt <= 0) {
      setError("Weight must be greater than 0.");
      return;
    }
    if (!Number.isInteger(q) || q < 1) {
      setError("Quantity must be a whole number, at least 1.");
      return;
    }
    if (p < 0) {
      setError("Padding cannot be negative.");
      return;
    }

    setLoading(true);
    try {
      const data = await createCustomBoxModel({
        item: {
          dimensions: { length: l, width: w, height: h },
          weight: wt,
          quantity: q,
        },
        padding: p,
      });
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Is the backend running?"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <h2>Custom Box Designer</h2>
      <p className="hint">Dimensions in mm, weight in kg, padding in mm per side.</p>

      <form onSubmit={handleSubmit}>
        <Field label="Length (mm)" value={length} onChange={setLength} />
        <Field label="Width (mm)" value={width} onChange={setWidth} />
        <Field label="Height (mm)" value={height} onChange={setHeight} />
        <Field label="Weight (kg)" value={weight} onChange={setWeight} />
        <Field label="Quantity" value={quantity} onChange={setQuantity} />
        <Field label="Padding per side (mm)" value={padding} onChange={setPadding} />

        <button type="submit" disabled={loading}>
          {loading ? "Calculating..." : "Design custom box"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="result">
          <h3>Result</h3>
          <p>
            Box size: {result.box_dimensions.length} ×{" "}
            {result.box_dimensions.width} × {result.box_dimensions.height} mm
          </p>
          <p>Volume: {result.volume.toLocaleString()} mm³</p>
          <p>Space used by item: {(result.utilization * 100).toFixed(1)}%</p>
        </div>
      )}
    </div>
  );
}