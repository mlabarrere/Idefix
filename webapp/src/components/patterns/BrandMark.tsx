// BrandMark — the ONLY component allowed to render the brand logo (§15.3).
// Screens never import the raw asset; they render <BrandMark />. The asset path,
// alt, aspect ratio and clear-space all come from brand.config (single source).
//
// The real (trademarked) logo is not committed to this public repo. When the
// asset at BRAND.logoSrc is absent, the mark falls back to the wordmark so the
// shell always shows *something* branded. Aspect ratio is locked → no distortion.
import { useState } from 'react'
import { BRAND } from '@/brand.config'

export function BrandMark({ className = '' }: { className?: string }) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <span
        className={`font-serif text-lg font-semibold tracking-tight text-accent ${className}`}
        style={{ padding: BRAND.clearSpacePx }}
      >
        {BRAND.wordmark}
      </span>
    )
  }

  return (
    <img
      src={BRAND.logoSrc}
      alt={BRAND.logoAlt}
      onError={() => setFailed(true)}
      className={`block h-6 w-auto ${className}`}
      style={{ aspectRatio: BRAND.logoAspect, margin: BRAND.clearSpacePx }}
    />
  )
}
