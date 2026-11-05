import { useState, useRef, useEffect } from 'react'
import type { DragEvent, ChangeEvent, FormEvent } from 'react'
import type { Product } from '../../types/customBox'
import { createProduct, uploadProductsCsv } from '../../services/productsApi'

interface AddProductModalProps {
  isOpen: boolean
  onClose: () => void
  onProductAdded: () => void
}

const COMMON_MATERIALS = [
  'Steel',
  'Hardened Steel',
  'Stainless Steel',
  'Aluminum',
  'Cast Aluminum',
  'Brass',
  'Bronze',
  'Copper',
  'Plastic (Nylon)',
  'Plastic (POM)',
  'Plastic (ABS)',
  'Rubber',
  'Cast Iron',
  'Wood',
]

const FEEDING_METHODS = [
  'Two-Bin System',
  'Bulk Feeding',
  'Kitting Cart',
  'Sequenced Delivery',
  'Conveyor Direct',
]

const INITIAL_FORM: Partial<Product> = {
  part_name: '',
  part_type: 'Aluminum',
  part_length: 120,
  part_breadth: 80,
  part_height: 50,
  part_weight: 0.8,
  standard_no_of_parts: 4,
  domestic_or_international: 'Domestic',
  per_day_requirement: 200,
  minimum_order_quantity: 400,
  line_feeding_method: 'Two-Bin System',
  model_file: '',
}

export default function AddProductModal({
  isOpen,
  onClose,
  onProductAdded,
}: AddProductModalProps) {
  const [formData, setFormData] = useState<Partial<Product>>(INITIAL_FORM)
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        handleClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  if (!isOpen) return null

  const handleClose = () => {
    setErrorMessage(null)
    setSuccessMessage(null)
    setCsvFile(null)
    setFormData(INITIAL_FORM)
    onClose()
  }

  // Handle CSV drag & drop
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0]
      if (file.name.toLowerCase().endsWith('.csv')) {
        setCsvFile(file)
        setErrorMessage(null)
      } else {
        setErrorMessage('Please drop a valid .csv file.')
      }
    }
  }

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0]
      if (file.name.toLowerCase().endsWith('.csv')) {
        setCsvFile(file)
        setErrorMessage(null)
      } else {
        setErrorMessage('Please select a valid .csv file.')
      }
    }
  }

  // Upload selected CSV file
  const handleUploadCsv = async () => {
    if (!csvFile) return
    setLoading(true)
    setErrorMessage(null)
    setSuccessMessage(null)

    try {
      const res = await uploadProductsCsv(csvFile)
      setSuccessMessage(res.message || `Successfully imported ${res.added_count} product(s)!`)
      onProductAdded()
      setTimeout(() => {
        handleClose()
      }, 1400)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to upload CSV file'
      setErrorMessage(msg)
    } finally {
      setLoading(false)
    }
  }

  // Handle manual form changes
  const handleInputChange = (
    e: ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'number' ? (value === '' ? '' : Number(value)) : value,
    }))
  }

  // Submit manual form
  const handleFormSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setErrorMessage(null)
    setSuccessMessage(null)

    if (!formData.part_name || !formData.part_name.trim()) {
      setErrorMessage('Part Name is required.')
      setLoading(false)
      return
    }

    try {
      const res = await createProduct({
        ...formData,
        part_name: formData.part_name.trim(),
        part_length: Number(formData.part_length) || 100,
        part_breadth: Number(formData.part_breadth) || 50,
        part_height: Number(formData.part_height) || 30,
        part_weight: Number(formData.part_weight) || 0.5,
        standard_no_of_parts: Number(formData.standard_no_of_parts) || 1,
        per_day_requirement: Number(formData.per_day_requirement) || 100,
        minimum_order_quantity: Number(formData.minimum_order_quantity) || 1,
      })

      setSuccessMessage(res.message || `Product '${formData.part_name}' added successfully!`)
      onProductAdded()
      setTimeout(() => {
        handleClose()
      }, 1200)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create product'
      setErrorMessage(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-add-product-title"
        className="relative bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[92vh] overflow-hidden border border-slate-200 z-10 flex flex-col"
      >
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-white shrink-0">
          <div>
            <h2
              id="modal-add-product-title"
              className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2"
            >
              <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
              Add New Product
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Upload a CSV file for batch parts, or enter specifications manually.
            </p>
          </div>

          <button
            type="button"
            onClick={handleClose}
            aria-label="Close dialog"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="p-5 overflow-y-auto space-y-4 flex-1">
          {/* Notification Messages */}
          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-800">
              <span className="text-base leading-none">⚠️</span>
              <div className="flex-1 font-medium">{errorMessage}</div>
            </div>
          )}

          {successMessage && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-2.5 text-xs text-emerald-800">
              <span className="text-base leading-none">✅</span>
              <div className="flex-1 font-medium">{successMessage}</div>
            </div>
          )}

          {/* 1. Drag & Drop CSV Box */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-5 text-center transition-all cursor-pointer select-none ${
              isDragging
                ? 'border-sky-500 bg-sky-50/70 scale-[0.99]'
                : csvFile
                ? 'border-emerald-400 bg-emerald-50/40'
                : 'border-slate-300 bg-slate-50/60 hover:bg-slate-100/60 hover:border-slate-400'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileInputChange}
              className="hidden"
            />

            <div className="flex flex-col items-center justify-center gap-1.5">
              <div
                className={`w-11 h-11 rounded-full flex items-center justify-center text-lg ${
                  csvFile
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-sky-100 text-sky-700'
                }`}
              >
                {csvFile ? '📄' : '📁'}
              </div>

              <div className="text-sm font-bold text-slate-800">
                {csvFile ? csvFile.name : 'Open with CSV'}
              </div>

              <p className="text-xs text-slate-500 max-w-sm">
                {csvFile
                  ? `${(csvFile.size / 1024).toFixed(1)} KB • Click to choose a different CSV file`
                  : 'Drag & drop a CSV file here, or click to browse from your computer'}
              </p>
            </div>

            {/* CSV Upload Action Button */}
            {csvFile && (
              <div className="mt-3.5 pt-3 border-t border-emerald-200/60 flex items-center justify-center gap-2">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleUploadCsv()
                  }}
                  disabled={loading}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  {loading ? (
                    <span>Importing CSV…</span>
                  ) : (
                    <>
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                      </svg>
                      <span>Upload & Import CSV Products</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    setCsvFile(null)
                  }}
                  disabled={loading}
                  className="px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-800 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  Clear
                </button>
              </div>
            )}
          </div>

          {/* 2. OR Divider */}
          <div className="relative my-2 flex items-center justify-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative bg-white px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              OR
            </div>
          </div>

          {/* 3. Manual Product Form */}
          <form onSubmit={handleFormSubmit} className="space-y-3.5">
            <div className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Enter Part Specifications
            </div>

            {/* Row 1: Part Name & Material */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Part Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  name="part_name"
                  value={formData.part_name || ''}
                  onChange={handleInputChange}
                  required
                  placeholder="e.g. Aluminum Mounting Bracket"
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Part Type / Material <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  name="part_type"
                  list="common-materials"
                  value={formData.part_type || ''}
                  onChange={handleInputChange}
                  required
                  placeholder="e.g. Aluminum, Steel, Plastic"
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900"
                />
                <datalist id="common-materials">
                  {COMMON_MATERIALS.map((mat) => (
                    <option key={mat} value={mat} />
                  ))}
                </datalist>
              </div>
            </div>

            {/* Row 2: Dimensions & Weight */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Length (mm) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  name="part_length"
                  value={formData.part_length ?? ''}
                  onChange={handleInputChange}
                  required
                  min="0.1"
                  step="0.1"
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Width (mm) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  name="part_breadth"
                  value={formData.part_breadth ?? ''}
                  onChange={handleInputChange}
                  required
                  min="0.1"
                  step="0.1"
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Height (mm) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  name="part_height"
                  value={formData.part_height ?? ''}
                  onChange={handleInputChange}
                  required
                  min="0.1"
                  step="0.1"
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Weight (kg) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  name="part_weight"
                  value={formData.part_weight ?? ''}
                  onChange={handleInputChange}
                  required
                  min="0.001"
                  step="0.01"
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900 font-mono"
                />
              </div>
            </div>

            {/* Row 3: SNP, Market, Per Day, MOQ */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Pack Qty (SNP) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  name="standard_no_of_parts"
                  value={formData.standard_no_of_parts ?? ''}
                  onChange={handleInputChange}
                  required
                  min="1"
                  step="1"
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Market
                </label>
                <select
                  name="domestic_or_international"
                  value={formData.domestic_or_international || 'Domestic'}
                  onChange={handleInputChange}
                  className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900"
                >
                  <option value="Domestic">Domestic</option>
                  <option value="International">International</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Per Day Req
                </label>
                <input
                  type="number"
                  name="per_day_requirement"
                  value={formData.per_day_requirement ?? ''}
                  onChange={handleInputChange}
                  min="0"
                  step="1"
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Min Order (MOQ)
                </label>
                <input
                  type="number"
                  name="minimum_order_quantity"
                  value={formData.minimum_order_quantity ?? ''}
                  onChange={handleInputChange}
                  min="1"
                  step="1"
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900 font-mono"
                />
              </div>
            </div>

            {/* Row 4: Line Feeding Method & CAD Model File */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Line Feeding Method
                </label>
                <select
                  name="line_feeding_method"
                  value={formData.line_feeding_method || 'Two-Bin System'}
                  onChange={handleInputChange}
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900"
                >
                  {FEEDING_METHODS.map((method) => (
                    <option key={method} value={method}>
                      {method}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  CAD Model Path <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <input
                  type="text"
                  name="model_file"
                  value={formData.model_file || ''}
                  onChange={handleInputChange}
                  placeholder="e.g. models/steel-bracket.step"
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-900"
                />
              </div>
            </div>

            {/* Submit Actions */}
            <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={handleClose}
                disabled={loading}
                className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-2xs transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <span>Saving…</span>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                    </svg>
                    <span>Submit & Add Product</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
