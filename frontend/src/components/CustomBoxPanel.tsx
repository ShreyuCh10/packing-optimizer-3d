import { createElement, useEffect, useState } from 'react'
import '@google/model-viewer'

import type { Product } from '../types/customBox'
import { fetchProducts } from '../services/productsApi'

import {
  createAutomaticCustomBoxes,
  createEmptyBoxModelFromResult,
  createPackedBoxModelFromResult,
  fetchMaterials,
  type AutomaticCustomBoxResult,
  type CustomBoxRequest,
  type PackagingMaterial,
} from '../services/customBoxApi'

interface CustomBoxPanelProps {
  initialProduct?: Product | null
  onBack?: () => void
}

type ConstraintValues = {
  maxLength: string
  maxWidth: string
  maxHeight: string
  maxWeight: string
}

function getDefaultConstraints(product: Product | null): ConstraintValues {
  return {
    maxLength: String(Math.max(600, product?.part_length ?? 0)+100),
    maxWidth: String(Math.max(400, product?.part_breadth ?? 0)+100),
    maxHeight: String(Math.max(600, product?.part_height ?? 0)+100),
    maxWeight: String(Math.max(25, (product?.part_weight ?? 0) + 10),
    ),
  }
}

function NumberField({
  label,
  value,
  unit,
  onChange,
}: {
  label: string
  value: string
  unit: string
  onChange: (value: string) => void
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <div className="flex items-center rounded-lg border border-slate-300 bg-white focus-within:ring-2 focus-within:ring-sky-500">
        <input
          type="number"
          min="0"
          step="any"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="w-full min-w-0 rounded-lg px-3 py-2.5 text-sm outline-none"
        />
        <span className="border-l border-slate-200 px-3 text-xs text-slate-500">
          {unit}
        </span>
      </div>
    </label>
  )
}

function ReadOnlyValue({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2.5">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-900">{value}</p>
    </div>
  )
}

function ModelViewer({
  src,
  height = '320px',
}: {
  src: string
  height?: string
}) {
  return createElement('model-viewer', {
    src,
    'camera-controls': true,
    'auto-rotate': true,
    'shadow-intensity': '1',
    'touch-action': 'pan-y',
    style: {
      width: '100%',
      height,
      backgroundColor: '#f8fafc',
    },
  })
}

function Metric({
  label,
  value,
}: {
  label: string
  value: string | number
}) {
  return (
    <div>
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-bold text-slate-900">{value}</p>
    </div>
  )
}

function groupIdenticalBoxes(
  boxes: AutomaticCustomBoxResult['boxes'],
) {
  const groups: {
    box: AutomaticCustomBoxResult['boxes'][number]
    count: number
  }[] = []

  const same = (a: number, b: number) => Math.abs(a - b) < 0.000001

  boxes.forEach((box) => {
    const existing = groups.find(({ box: first }) =>
      first.units_packed === box.units_packed &&
      same(first.box_dimensions.length, box.box_dimensions.length) &&
      same(first.box_dimensions.width, box.box_dimensions.width) &&
      same(first.box_dimensions.height, box.box_dimensions.height) &&
      same(first.padding_used, box.padding_used) &&
      same(first.wall_thickness_mm, box.wall_thickness_mm) &&
      same(first.total_product_weight_kg, box.total_product_weight_kg) &&
      same(first.packaging_weight_kg, box.packaging_weight_kg) &&
      same(first.total_weight_kg, box.total_weight_kg) &&
      same(first.utilization, box.utilization) &&
      first.placements.length === box.placements.length &&
      first.placements.every((placement, placementIndex) => {
        const other = box.placements[placementIndex]
        return (
          same(placement.position[0], other.position[0]) &&
          same(placement.position[1], other.position[1]) &&
          same(placement.position[2], other.position[2]) &&
          same(placement.size.length, other.size.length) &&
          same(placement.size.width, other.size.width) &&
          same(placement.size.height, other.size.height)
        )
      }),
    )

    if (existing) {
      existing.count += 1
    } else {
      groups.push({ box, count: 1 })
    }
  })

  return groups
}

export default function CustomBoxPanel({
  initialProduct = null,
  onBack,
}: CustomBoxPanelProps) {
  const isProductPreselected = initialProduct !== null

  const [products, setProducts] = useState<Product[]>([])
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [productsError, setProductsError] = useState('')
  const [selectedProduct, setSelectedProduct] =
    useState<Product | null>(initialProduct)

  const [materials, setMaterials] = useState<PackagingMaterial[]>([])
  const [loadingMaterials, setLoadingMaterials] = useState(true)
  const [materialsError, setMaterialsError] = useState('')
  const [selectedMaterialId, setSelectedMaterialId] = useState('')

  const [constraints, setConstraints] = useState<ConstraintValues>(
    () => getDefaultConstraints(initialProduct),
  )
  const [draftConstraints, setDraftConstraints] =
    useState<ConstraintValues>(constraints)
  const [isEditingConstraints, setIsEditingConstraints] = useState(false)
  const [showQuantityEntry, setShowQuantityEntry] = useState(false)
  const [totalQuantity, setTotalQuantity] = useState('1500')

  const [error, setError] = useState('')
  const [automaticResult, setAutomaticResult] =
    useState<AutomaticCustomBoxResult | null>(null)
  const [optimizing, setOptimizing] = useState(false)

  const [emptyModelUrls, setEmptyModelUrls] = useState<string[]>([])
  const [packedModelUrls, setPackedModelUrls] = useState<string[]>([])
  const [modelErrors, setModelErrors] = useState<string[]>([])
  const [emptyModelErrors, setEmptyModelErrors] = useState<string[]>([])

  const [showEmptyPreview, setShowEmptyPreview] = useState(false)
  const [showPackedPreview, setShowPackedPreview] = useState(false)

  const [emptySelectedIndex, setEmptySelectedIndex] = useState(0)
  const [packedSelectedIndex, setPackedSelectedIndex] = useState(0)

  const [showMeasurements, setShowMeasurements] = useState(false)
  const [updatingMeasurements, setUpdatingMeasurements] = useState(false)

  useEffect(() => {
    let active = true

    const loadData = async () => {
      try {
        const data = await fetchProducts()
        if (active) {
          setProducts(data.products)
          setProductsError('')
        }
      } catch (err) {
        if (active) {
          setProductsError(
            err instanceof Error ? err.message : 'Unable to load products.',
          )
        }
      } finally {
        if (active) setLoadingProducts(false)
      }

      try {
        const data = await fetchMaterials()
        if (active) {
          setMaterials(data)
          setMaterialsError('')
          if (data.length > 0) setSelectedMaterialId(data[0].id)
        }
      } catch (err) {
        if (active) {
          setMaterialsError(
            err instanceof Error
              ? err.message
              : 'Unable to load packaging materials.',
          )
        }
      } finally {
        if (active) setLoadingMaterials(false)
      }
    }

    void loadData()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    return () => {
      emptyModelUrls.forEach((url) => URL.revokeObjectURL(url))
      packedModelUrls.forEach((url) => {
        if (url) URL.revokeObjectURL(url)
      })
    }
  }, [emptyModelUrls, packedModelUrls])

  function clearModels() {
    setEmptyModelUrls([])
    setPackedModelUrls([])
    setModelErrors([])
    setEmptyModelErrors([])
    setShowEmptyPreview(false)
    setShowPackedPreview(false)
    setEmptySelectedIndex(0)
    setPackedSelectedIndex(0)
    setShowMeasurements(false)
  }

  function clearResults() {
    setAutomaticResult(null)
    setError('')
    clearModels()
  }

  function handleProductChange(name: string) {
    const product = products.find((item) => item.part_name === name) ?? null

    setSelectedProduct(product)

    const defaultConstraints = getDefaultConstraints(product)
    setConstraints(defaultConstraints)
    setDraftConstraints(defaultConstraints)

    clearResults()
  }

  function beginConstraintEdit() {
    setDraftConstraints({ ...constraints })
    setIsEditingConstraints(true)
    setError('')
  }

  function cancelConstraintEdit() {
    setDraftConstraints({ ...constraints })
    setIsEditingConstraints(false)
  }

  function saveConstraints() {
    const values = [
      Number(draftConstraints.maxLength),
      Number(draftConstraints.maxWidth),
      Number(draftConstraints.maxHeight),
      Number(draftConstraints.maxWeight),
    ]

    if (values.some((value) => !Number.isFinite(value) || value <= 0)) {
      setError(
        'All maximum dimensions and lifting weight must be greater than zero.',
      )
      return
    }

    setConstraints({ ...draftConstraints })
    setIsEditingConstraints(false)
    setError('')
    clearResults()
  }

  async function generatePreviews(
    groups: ReturnType<typeof groupIdenticalBoxes>,
    modelFile?: string,
  ) {
    const previews = await Promise.all(
      groups.map(async ({ box }) => {
        const [emptyModel, packedModel] = await Promise.allSettled([
          createEmptyBoxModelFromResult(box),
          modelFile
            ? createPackedBoxModelFromResult(box, modelFile)
            : Promise.reject(
                new Error(
                  'A 3D product model is not available for this product.',
                ),
              ),
        ])

        return {
          emptyUrl:
            emptyModel.status === 'fulfilled' ? emptyModel.value : '',
          packedUrl:
            packedModel.status === 'fulfilled' ? packedModel.value : '',
          error:
            packedModel.status === 'rejected'
              ? packedModel.reason instanceof Error
                ? packedModel.reason.message
                : 'Unable to generate the product preview.'
              : '',
          emptyError:
            emptyModel.status === 'rejected'
              ? emptyModel.reason instanceof Error
                ? emptyModel.reason.message
                : 'Unable to generate the empty box preview.'
              : '',
        }
      }),
    )

    setEmptyModelUrls(previews.map((preview) => preview.emptyUrl))
    setPackedModelUrls(previews.map((preview) => preview.packedUrl))
    setModelErrors(previews.map((preview) => preview.error))
    setEmptyModelErrors(previews.map((preview) => preview.emptyError))
  }

  async function handleMeasurementsToggle() {
    if (!automaticResult || updatingMeasurements) {
      return
    }

    const nextValue = !showMeasurements
    setUpdatingMeasurements(true)
    setEmptyModelErrors([])

    try {
      const groups = groupIdenticalBoxes(automaticResult.boxes)

      const generatedModels = await Promise.allSettled(
        groups.map(({ box }) =>
          createEmptyBoxModelFromResult(box, nextValue),
        ),
      )

      const failedModel = generatedModels.find(
        (result) => result.status === 'rejected',
      )

      if (failedModel?.status === 'rejected') {
        generatedModels.forEach((result) => {
          if (result.status === 'fulfilled') {
            URL.revokeObjectURL(result.value)
          }
        })

        const message =
          failedModel.reason instanceof Error
            ? failedModel.reason.message
            : 'Unable to update the measurement preview.'

        setEmptyModelErrors([message])
        return
      }

      const newUrls = generatedModels.map((result) =>
        result.status === 'fulfilled' ? result.value : '',
      )

      setEmptyModelUrls(newUrls)
      setShowMeasurements(nextValue)
    } finally {
      setUpdatingMeasurements(false)
    }
  }

  async function handleOptimize() {
    if (!selectedProduct) {
      setError('Please select a product first.')
      return
    }

    if (materials.length === 0 || !selectedMaterialId) {
      setError('Packaging materials are still loading or unavailable.')
      return
    }

    const quantity = Number(totalQuantity)
    if (!Number.isInteger(quantity) || quantity < 1) {
      setError('Enter a valid total quantity (a positive whole number).')
      return
    }

    const dimensions = {
      length: Number(constraints.maxLength),
      width: Number(constraints.maxWidth),
      height: Number(constraints.maxHeight),
    }
    const maxWeight = Number(constraints.maxWeight)

    if (
      Object.values(dimensions).some(
        (value) => !Number.isFinite(value) || value <= 0,
      ) ||
      !Number.isFinite(maxWeight) ||
      maxWeight <= 0
    ) {
      setError(
        'Please check the saved constraints. All values must be greater than zero.',
      )
      return
    }

    setError('')
    setAutomaticResult(null)
    clearModels()
    setOptimizing(true)

    const baseRequest: CustomBoxRequest = {
      item: {
        item_type: selectedProduct.part_type,
        model_file: selectedProduct.model_file ?? undefined,
        dimensions: {
          length: selectedProduct.part_length,
          width: selectedProduct.part_breadth,
          height: selectedProduct.part_height,
        },
        weight: selectedProduct.part_weight,
      },
      constraints: {
        max_box_dimensions: dimensions,
        max_human_lifting_weight_kg: maxWeight,
        // The automatic backend derives padding from product type and
        // wall thickness from the selected material configuration.
        // These values satisfy the current API request schema only.
        padding_per_side_mm: 0,
        wall_thickness_mm: 1,
        material_id: selectedMaterialId,
      },
    }

    try {
      const response = await createAutomaticCustomBoxes({
        item: baseRequest.item,
        total_quantity: quantity,
        constraints: baseRequest.constraints,
      })

      setAutomaticResult(response)

      const boxGroups = groupIdenticalBoxes(response.boxes)
      if (boxGroups.length > 0) {
        await generatePreviews(
          boxGroups,
          selectedProduct.model_file ?? undefined,
        )
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Optimization failed.')
    } finally {
      setOptimizing(false)
    }
  }

  const boxGroups = automaticResult
    ? groupIdenticalBoxes(automaticResult.boxes)
    : []
  const selectedEmptyGroup = boxGroups[emptySelectedIndex]
  const selectedPackedGroup = boxGroups[packedSelectedIndex]

  return (
    <div className="space-y-6">
      <header>
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="mb-5 inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          >
            <span aria-hidden="true">←</span>
            Back
          </button>
        )}

        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-600">
          Packaging optimization
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
          Custom Box Optimizer
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Select a product, review your standard constraints, and calculate an
          automatic packaging plan.
        </p>
      </header>

      {/* Product selection remains connected to the existing product dataset. */}
      <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="font-semibold text-slate-900">1. Product selection</h2>
          <p className="mt-1 text-sm text-slate-500">
            {isProductPreselected
              ? 'Product selected from the product catalog.'
              : 'Choose a product from the existing product dataset.'}
          </p>
        </div>

        <div className="space-y-4 p-5">
          {!isProductPreselected && (
            <label className="flex flex-col gap-2">
              <span className="text-sm font-medium text-slate-700">
                Select product
              </span>
              <select
                value={selectedProduct?.part_name ?? ''}
                onChange={(event) => handleProductChange(event.target.value)}
                disabled={loadingProducts || products.length === 0}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-sky-500 disabled:bg-slate-100"
              >
                <option value="">
                  {loadingProducts
                    ? 'Loading products...'
                    : products.length > 0
                      ? 'Select a product'
                      : 'No products available'}
                </option>
                {products.map((product) => (
                  <option key={product.part_name} value={product.part_name}>
                    {product.part_name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {!isProductPreselected && productsError && (
            <p className="text-sm text-amber-700">
              Unable to load products: {productsError}
            </p>
          )}

          {selectedProduct && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="mb-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {isProductPreselected ? 'Selected product' : 'Product details'}
                </p>
                <h3 className="mt-1 text-lg font-semibold text-slate-900">
                  {selectedProduct.part_name}
                </h3>
              </div>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <Metric
                  label="Length"
                  value={`${selectedProduct.part_length} mm`}
                />
                <Metric
                  label="Width"
                  value={`${selectedProduct.part_breadth} mm`}
                />
                <Metric
                  label="Height"
                  value={`${selectedProduct.part_height} mm`}
                />
                <Metric
                  label="Unit weight"
                  value={`${selectedProduct.part_weight} kg`}
                />
                <div className="col-span-2 sm:col-span-4">
                  <p className="text-xs text-slate-500">Part type</p>
                  <p className="mt-1 font-semibold text-slate-900">
                    {selectedProduct.part_type}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Standard constraints: read-only unless Set Constraints is clicked. */}
      <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div>
            <h2 className="font-semibold text-slate-900">2. Standard constraints</h2>
            <p className="mt-1 text-sm text-slate-500">
              Default limits used when designing the boxes.
            </p>
          </div>
          {!isEditingConstraints && (
            <button
              type="button"
              onClick={beginConstraintEdit}
              className="shrink-0 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-sky-400 hover:bg-sky-50"
            >
              Set Constraints
            </button>
          )}
        </div>

        <div className="space-y-4 p-5">
          {isEditingConstraints ? (
            <>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <NumberField
                  label="Maximum box length"
                  value={draftConstraints.maxLength}
                  unit="mm"
                  onChange={(value) =>
                    setDraftConstraints((current) => ({
                      ...current,
                      maxLength: value,
                    }))
                  }
                />
                <NumberField
                  label="Maximum box width"
                  value={draftConstraints.maxWidth}
                  unit="mm"
                  onChange={(value) =>
                    setDraftConstraints((current) => ({
                      ...current,
                      maxWidth: value,
                    }))
                  }
                />
                <NumberField
                  label="Maximum box height"
                  value={draftConstraints.maxHeight}
                  unit="mm"
                  onChange={(value) =>
                    setDraftConstraints((current) => ({
                      ...current,
                      maxHeight: value,
                    }))
                  }
                />
                <NumberField
                  label="Maximum human lifting weight"
                  value={draftConstraints.maxWeight}
                  unit="kg"
                  onChange={(value) =>
                    setDraftConstraints((current) => ({
                      ...current,
                      maxWeight: value,
                    }))
                  }
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={cancelConstraintEdit}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={saveConstraints}
                  className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700"
                >
                  Set / Save
                </button>
              </div>
            </>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <ReadOnlyValue
                label="Maximum length"
                value={`${constraints.maxLength} mm`}
              />
              <ReadOnlyValue
                label="Maximum width"
                value={`${constraints.maxWidth} mm`}
              />
              <ReadOnlyValue
                label="Maximum height"
                value={`${constraints.maxHeight} mm`}
              />
              <ReadOnlyValue
                label="Maximum lifting weight"
                value={`${constraints.maxWeight} kg`}
              />
            </div>
          )}
        </div>
      </section>

      {/* Quantity entry is opened by the user's explicit action. */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold text-slate-900">3. Automatic box design</h2>
            <p className="mt-1 text-sm text-slate-500">
              Accept the constraints above, then enter the number of products to pack.
            </p>
          </div>
          {!showQuantityEntry && (
            <button
              type="button"
              onClick={() => {
                setShowQuantityEntry(true)
                setError('')
              }}
              disabled={!selectedProduct || isEditingConstraints}
              className="rounded-lg bg-sky-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Enter Product Quantity
            </button>
          )}
        </div>

        {showQuantityEntry && (
          <div className="mt-5 space-y-4 border-t border-slate-100 pt-5">
            <div>
              <p className="mb-3 text-sm font-semibold text-slate-700">
                Constraints to be applied
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <ReadOnlyValue
                  label="Maximum length"
                  value={`${constraints.maxLength} mm`}
                />
                <ReadOnlyValue
                  label="Maximum width"
                  value={`${constraints.maxWidth} mm`}
                />
                <ReadOnlyValue
                  label="Maximum height"
                  value={`${constraints.maxHeight} mm`}
                />
                <ReadOnlyValue
                  label="Maximum lifting weight"
                  value={`${constraints.maxWeight} kg`}
                />
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Need to change a value? Use Set Constraints above before calculating.
              </p>
            </div>

            <div className="max-w-sm">
              <NumberField
                label="Total product quantity"
                value={totalQuantity}
                unit="units"
                onChange={(value) => {
                  setTotalQuantity(value)
                  clearResults()
                }}
              />
            </div>

            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowQuantityEntry(false)
                  setError('')
                }}
                className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleOptimize}
                disabled={
                  optimizing ||
                  loadingMaterials ||
                  loadingProducts ||
                  !selectedProduct ||
                  materials.length === 0
                }
                className="rounded-lg bg-sky-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {optimizing ? 'Calculating...' : 'Calculate Automatic Box Plan'}
              </button>
            </div>
          </div>
        )}

        {materialsError && (
          <p className="mt-3 text-sm text-amber-700">
            Unable to load material configuration: {materialsError}
          </p>
        )}
        {loadingMaterials && (
          <p className="mt-3 text-xs text-slate-500">
            Loading packaging material configuration...
          </p>
        )}
      </section>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Automatic calculation results. */}
      {automaticResult && (
        <section className="space-y-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              4. Automatic optimization results
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Packaging plan for {automaticResult.total_quantity} units.
            </p>
          </div>

          <div className="rounded-lg bg-slate-50 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Selected packaging material
            </p>
            <p className="mt-1 text-lg font-semibold text-slate-900">
              {automaticResult.material_name}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            <Metric label="Total quantity" value={automaticResult.total_quantity} />
            <Metric label="Boxes required" value={automaticResult.boxes_required} />
            <Metric
              label="Total product weight"
              value={`${automaticResult.total_product_weight_kg.toFixed(3)} kg`}
            />
            <Metric
              label="Total packaging weight"
              value={`${automaticResult.total_packaging_weight_kg.toFixed(3)} kg`}
            />
            <Metric
              label="Total shipment weight"
              value={`${automaticResult.total_weight_kg.toFixed(3)} kg`}
            />
          </div>

          <div>
            <h3 className="mb-3 font-semibold text-slate-900">
              Individual box details
            </h3>
            <div className="space-y-4">
              {groupIdenticalBoxes(automaticResult.boxes).map(({ box, count }, index) => (
                <div
                  key={index}
                  className="rounded-lg border border-slate-200 p-4"
                >
                  <h4 className="font-semibold text-slate-900">
                    Box {index + 1} ({count} {count === 1 ? 'Box' : 'Identical Boxes'})
                  </h4>
                  <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                    <Metric label="Units packed" value={box.units_packed} />
                    <Metric
                      label="Length"
                      value={`${box.box_dimensions.length} mm`}
                    />
                    <Metric
                      label="Width"
                      value={`${box.box_dimensions.width} mm`}
                    />
                    <Metric
                      label="Height"
                      value={`${box.box_dimensions.height} mm`}
                    />
                    <Metric
                      label="Calculated padding"
                      value={`${box.padding_used} mm`}
                    />
                    <Metric
                      label="Calculated wall thickness"
                      value={`${box.wall_thickness_mm} mm`}
                    />
                    <Metric
                      label="Product weight"
                      value={`${box.total_product_weight_kg.toFixed(3)} kg`}
                    />
                    <Metric
                      label="Packaging weight"
                      value={`${box.packaging_weight_kg.toFixed(3)} kg`}
                    />
                    <Metric
                      label="Total box weight"
                      value={`${box.total_weight_kg.toFixed(3)} kg`}
                    />
                    <Metric
                      label="Volume utilization"
                      value={`${(box.utilization * 100).toFixed(2)}%`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Separate compact previews with independent enlarged views. */}
      <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Empty box preview</h2>
            <button
              type="button"
              onClick={() => {
                setEmptySelectedIndex(0)
                setShowEmptyPreview(true)
              }}
              disabled={!emptyModelUrls.some(Boolean)}
              aria-label="Enlarge empty box preview"
              title="Enlarge preview"
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-lg text-slate-600 transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ⛶
            </button>
          </div>
          <div className="mt-4 min-h-64 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
            {emptyModelUrls[0] ? (
              <ModelViewer src={emptyModelUrls[0]} />
            ) : (
              <div className="flex min-h-64 items-center justify-center px-4 text-center">
                <p className="text-sm text-slate-400">
                  {emptyModelErrors[0] ||
                    (automaticResult
                      ? 'Empty box preview is unavailable.'
                      : 'Calculate a box plan to view the 3D model.')}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Box with products</h2>
            <button
              type="button"
              onClick={() => {
                setPackedSelectedIndex(0)
                setShowPackedPreview(true)
              }}
              disabled={!packedModelUrls.some(Boolean)}
              aria-label="Enlarge packed box preview"
              title="Enlarge preview"
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-lg text-slate-600 transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ⛶
            </button>
          </div>
          <div className="mt-4 min-h-64 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
            {packedModelUrls[0] ? (
              <ModelViewer src={packedModelUrls[0]} />
            ) : (
              <div className="flex min-h-64 items-center justify-center px-4 text-center">
                <p className="text-sm text-slate-400">
                  {modelErrors[0] ||
                    (automaticResult
                      ? 'Packed box preview is unavailable.'
                      : 'Calculate a box plan to view the product arrangement.')}
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Enlarged empty-box preview. */}
      {showEmptyPreview &&
        selectedEmptyGroup &&
        emptyModelUrls[emptySelectedIndex] && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-3 sm:p-6"
            role="dialog"
            aria-modal="true"
            aria-label="Empty box 3D preview"
            onClick={() => setShowEmptyPreview(false)}
          >
            <div
              className="flex max-h-[94vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">
                    Empty box preview
                  </h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Inspect the dimensions of each calculated box type.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowEmptyPreview(false)}
                  aria-label="Close empty box preview"
                  className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 text-xl text-slate-500 hover:bg-slate-50"
                >
                  ×
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-3">
                <div className="flex min-w-0 flex-1 gap-2 overflow-x-auto pb-1">
                  {boxGroups.map((group, index) => (
                    <button
                      key={`empty-tab-${index}`}
                      type="button"
                      onClick={() => setEmptySelectedIndex(index)}
                      className={`shrink-0 rounded-full border px-4 py-2 text-xs font-semibold transition ${
                        emptySelectedIndex === index
                          ? 'border-sky-500 bg-sky-50 text-sky-700'
                          : 'border-slate-200 bg-white text-slate-600 hover:border-sky-300'
                      }`}
                    >
                      Box {index + 1} · {group.count}{' '}
                      {group.count === 1 ? 'Box' : 'Boxes'}
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setEmptySelectedIndex((current) =>
                      Math.max(0, current - 1),
                    )
                  }
                  disabled={emptySelectedIndex === 0}
                  aria-label="Previous box type"
                  className="h-8 w-8 shrink-0 rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                >
                  ‹
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setEmptySelectedIndex((current) =>
                      Math.min(boxGroups.length - 1, current + 1),
                    )
                  }
                  disabled={emptySelectedIndex >= boxGroups.length - 1}
                  aria-label="Next box type"
                  className="h-8 w-8 shrink-0 rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                >
                  ›
                </button>
              </div>

              <div className="flex items-center justify-between gap-4 px-5 py-3">
                <div>
                  <p className="text-sm font-semibold text-slate-800">
                    Box {emptySelectedIndex + 1}
                  </p>
                  <p className="text-xs text-slate-500">
                    {selectedEmptyGroup.count} identical{' '}
                    {selectedEmptyGroup.count === 1 ? 'box' : 'boxes'}
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={showMeasurements}
                  onClick={handleMeasurementsToggle}
                  disabled={updatingMeasurements}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-sky-300 disabled:cursor-wait disabled:opacity-60"
                >
                  {updatingMeasurements
                    ? 'Updating...'
                    : showMeasurements
                      ? 'Hide Measurements'
                      : 'Show Measurements'}
                  <span
                    className={`relative h-5 w-9 rounded-full transition ${
                      showMeasurements ? 'bg-sky-600' : 'bg-slate-300'
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition ${
                        showMeasurements ? 'left-[18px]' : 'left-0.5'
                      }`}
                    />
                  </span>
                </button>
              </div>

              <div className="overflow-y-auto px-5 pb-5">
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
                  <ModelViewer
                    src={emptyModelUrls[emptySelectedIndex]}
                    height="min(58vh, 560px)"
                  />
                </div>
                {showMeasurements && (
                  <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs font-medium">
                    <span className="inline-flex items-center gap-2 text-red-600">
                      <span className="h-0.5 w-5 bg-red-500" />
                      Length: {selectedEmptyGroup.box.box_dimensions.length} mm
                    </span>
                    <span className="inline-flex items-center gap-2 text-green-600">
                      <span className="h-0.5 w-5 bg-green-500" />
                      Width: {selectedEmptyGroup.box.box_dimensions.width} mm
                    </span>
                    <span className="inline-flex items-center gap-2 text-blue-600">
                      <span className="h-0.5 w-5 bg-blue-500" />
                      Height: {selectedEmptyGroup.box.box_dimensions.height} mm
                    </span>
                  </div>
                )}
                {emptyModelErrors[emptySelectedIndex] && (
                  <p className="mt-3 text-sm text-red-600">
                    {emptyModelErrors[emptySelectedIndex]}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

      {/* Enlarged packed-box preview. */}
      {showPackedPreview &&
        selectedPackedGroup &&
        packedModelUrls[packedSelectedIndex] && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-3 sm:p-6"
            role="dialog"
            aria-modal="true"
            aria-label="Packed box 3D preview"
            onClick={() => setShowPackedPreview(false)}
          >
            <div
              className="flex max-h-[94vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">
                    Box with products
                  </h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Inspect the actual product arrangement inside each box type.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowPackedPreview(false)}
                  aria-label="Close packed box preview"
                  className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 text-xl text-slate-500 hover:bg-slate-50"
                >
                  ×
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-3">
                <div className="flex min-w-0 flex-1 gap-2 overflow-x-auto pb-1">
                  {boxGroups.map((group, index) => (
                    <button
                      key={`packed-tab-${index}`}
                      type="button"
                      onClick={() => setPackedSelectedIndex(index)}
                      className={`shrink-0 rounded-full border px-4 py-2 text-xs font-semibold transition ${
                        packedSelectedIndex === index
                          ? 'border-sky-500 bg-sky-50 text-sky-700'
                          : 'border-slate-200 bg-white text-slate-600 hover:border-sky-300'
                      }`}
                    >
                      Box {index + 1} · {group.count}{' '}
                      {group.count === 1 ? 'Box' : 'Boxes'}
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setPackedSelectedIndex((current) =>
                      Math.max(0, current - 1),
                    )
                  }
                  disabled={packedSelectedIndex === 0}
                  aria-label="Previous box type"
                  className="h-8 w-8 shrink-0 rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                >
                  ‹
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setPackedSelectedIndex((current) =>
                      Math.min(boxGroups.length - 1, current + 1),
                    )
                  }
                  disabled={packedSelectedIndex >= boxGroups.length - 1}
                  aria-label="Next box type"
                  className="h-8 w-8 shrink-0 rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                >
                  ›
                </button>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
                <div>
                  <p className="text-sm font-semibold text-slate-800">
                    Box {packedSelectedIndex + 1}
                  </p>
                  <p className="text-xs text-slate-500">
                    {selectedPackedGroup.count} identical{' '}
                    {selectedPackedGroup.count === 1 ? 'box' : 'boxes'}
                  </p>
                </div>
                <div className="rounded-xl border border-sky-100 bg-sky-50 px-4 py-2 text-right">
                  <p className="text-lg font-bold leading-tight text-sky-800">
                    {selectedPackedGroup.box.units_packed}
                  </p>
                  <p className="mt-0.5 text-[11px] font-semibold text-sky-700">
                    Products per Box
                  </p>
                </div>
              </div>

              <div className="overflow-y-auto px-5 pb-5">
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
                  <ModelViewer
                    src={packedModelUrls[packedSelectedIndex]}
                    height="min(58vh, 560px)"
                  />
                </div>
              </div>
            </div>
          </div>
        )}
    </div>
  )
}