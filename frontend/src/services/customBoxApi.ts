
const API_URL = "http://localhost:8000";

export type CustomBoxRequest = {
  item: {
    item_type: string;
    model_file?: string;
    dimensions: {
      length: number;
      width: number;
      height: number;
    };
    weight: number;
    quantity?: number;
  };
  constraints: {
    max_box_dimensions: {
      length: number;
      width: number;
      height: number;
    };
    max_human_lifting_weight_kg: number;
    padding_per_side_mm: number;
    wall_thickness_mm: number;
    material_id: string;
  };
};

export type CustomBoxResult = {
  box_dimensions: {
    length: number;
    width: number;
    height: number;
  };
  volume: number;
  utilization: number;
  padding_used: number;
  units_packed: number;

  placements: {
    position: [number, number, number];
    size: {
      length: number;
      width: number;
      height: number;
    };
  }[];

  // Weight calculations
  product_unit_weight_kg: number;
  total_product_weight_kg: number;
  packaging_weight_kg: number;
  total_weight_kg: number;

  // Packaging material details
  material_id: string;
  material_name: string;
  wall_thickness_mm: number;
};

// Automatic box planning request
export type AutomaticCustomBoxRequest = {
  item: {
    item_type: string;
    model_file?: string;
    dimensions: {
      length: number;
      width: number;
      height: number;
    };
    weight: number;
  };
  total_quantity: number;
  constraints: {
    max_box_dimensions: {
      length: number;
      width: number;
      height: number;
    };
    max_human_lifting_weight_kg: number;
    padding_per_side_mm: number;
    wall_thickness_mm: number;
    material_id: string;
  };
};

// Automatic box planning response
export type AutomaticCustomBoxResult = {
  total_quantity: number;
  boxes_required: number;
  material_id: string;
  material_name: string;
  boxes: CustomBoxResult[];

  total_product_weight_kg: number;
  total_packaging_weight_kg: number;
  total_weight_kg: number;
  estimated_packaging_cost: number;
};

export type PackagingMaterial = {
  id: string;
  name: string;
  wall_thickness_mm: number;
  max_weight_kg: number;
  density_kg_m3: number;
  burst_strength_kpa: number;
  cost_per_sqm: number;
};

// Fetch packaging materials
export async function fetchMaterials(): Promise<PackagingMaterial[]> {
  const response = await fetch(`${API_URL}/materials`);

  if (!response.ok) {
    throw new Error("Unable to load packaging materials.");
  }

  const data = await response.json();
  return data.materials;
}

// Manual box calculation
export async function createCustomBox(
  request: CustomBoxRequest
): Promise<CustomBoxResult> {
  const response = await fetch(`${API_URL}/custom-box`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Custom box optimization failed.");
  }

  return response.json();
}

// Automatic box calculation
export async function createAutomaticCustomBoxes(
  request: AutomaticCustomBoxRequest
): Promise<AutomaticCustomBoxResult> {
  const response = await fetch(`${API_URL}/custom-box/automatic`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(
      error.detail || "Automatic custom box optimization failed."
    );
  }

  return response.json();
}

// Existing 3D model functions

export async function createCustomBoxModel(
  request: CustomBoxRequest
): Promise<string> {
  const response = await fetch(`${API_URL}/custom-box/model`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Unable to generate 3D model.");
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export async function createEmptyBoxModel(
  request: CustomBoxRequest
): Promise<string> {
  const response = await fetch(`${API_URL}/custom-box/empty-model`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Unable to generate empty box.");
  }

  return URL.createObjectURL(await response.blob());
}

export async function createPackedBoxModel(
  request: CustomBoxRequest
): Promise<string> {
  const response = await fetch(`${API_URL}/custom-box/packed-model`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Unable to generate packed box.");
  }

  return URL.createObjectURL(await response.blob());
}

// Generate an empty box preview from an existing optimization result.
// Measurement lines are included only when showMeasurements is true.
export async function createEmptyBoxModelFromResult(
  result: CustomBoxResult,
  showMeasurements: boolean = false
): Promise<string> {
  const response = await fetch(`${API_URL}/custom-box/empty-model/result`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      result,
      include_measurements: showMeasurements,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Unable to generate empty box.");
  }

  return URL.createObjectURL(await response.blob());
}

export async function createPackedBoxModelFromResult(
  result: CustomBoxResult,
  modelFile: string
): Promise<string> {
  const response = await fetch(`${API_URL}/custom-box/packed-model/result`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      result,
      model_file: modelFile,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Unable to generate packed box.");
  }

  return URL.createObjectURL(await response.blob());
}
