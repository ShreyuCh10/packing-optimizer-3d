export interface MaterialBadgeStyle {
  bg: string
  text: string
  border: string
}

/**
 * Returns soft-colored badge styling classes based on material / part type.
 * Adheres to strictly flat solid colors (no gradients).
 */
export function getMaterialBadgeStyle(material?: string): MaterialBadgeStyle {
  const m = (material || '').toLowerCase()

  // Aluminum and alloys -> Soft Sky Blue
  if (m.includes('aluminum')) {
    return {
      bg: 'bg-sky-50',
      text: 'text-sky-700',
      border: 'border-sky-200',
    }
  }

  // Brass, Bronze, Copper -> Soft Amber / Warm Bronze
  if (m.includes('brass') || m.includes('bronze') || m.includes('copper')) {
    return {
      bg: 'bg-amber-50',
      text: 'text-amber-800',
      border: 'border-amber-200',
    }
  }

  // Plastics (ABS, Nylon, POM, Polycarbonate, HDPE) -> Soft Teal
  if (
    m.includes('plastic') ||
    m.includes('hdpe') ||
    m.includes('pom') ||
    m.includes('abs') ||
    m.includes('nylon') ||
    m.includes('polycarbonate') ||
    m.includes('polymer')
  ) {
    return {
      bg: 'bg-teal-50',
      text: 'text-teal-800',
      border: 'border-teal-200',
    }
  }

  // Acrylic / Glass -> Soft Indigo
  if (m.includes('glass') || m.includes('acrylic')) {
    return {
      bg: 'bg-indigo-50',
      text: 'text-indigo-700',
      border: 'border-indigo-200',
    }
  }

  // Carbon Fiber -> Soft Slate / Graphite
  if (m.includes('carbon')) {
    return {
      bg: 'bg-zinc-100',
      text: 'text-zinc-800',
      border: 'border-zinc-300',
    }
  }

  // Rubber / Elastomers / Foam -> Soft Rose
  if (m.includes('rubber') || m.includes('epdm') || m.includes('foam')) {
    return {
      bg: 'bg-rose-50',
      text: 'text-rose-700',
      border: 'border-rose-200',
    }
  }

  // Steel, Iron, Sheet metal, and general ferrous metals -> Soft Slate / Cool Gray
  if (m.includes('steel') || m.includes('iron') || m.includes('sheet metal')) {
    return {
      bg: 'bg-slate-100',
      text: 'text-slate-700',
      border: 'border-slate-300',
    }
  }

  // Default neutral soft badge
  return {
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-200',
  }
}

