// Central brand + signature config — the SINGLE source of truth consumed by the
// BrandMark and Signature patterns (§15). Nothing else may hardcode the logo
// path or the signer: change the brand or the author here, once.
//
// Trademark note: `logoSrc` is the brand logo under public/brand/. The Accenture
// mark is a registered trademark of Accenture; it is included here at the repo
// owner's direction. If BrandMark's asset is ever absent, it falls back to the
// wordmark, so the app always renders.
export const BRAND = {
  /** Product wordmark shown when no logo asset is present (fallback). */
  wordmark: '◆ IDÉFIX',
  /** Path (public/) to the brand logo asset. Owner-provided, git-ignored. */
  logoSrc: '/brand/mark.svg',
  /** Alt text — a brand proper noun, deliberately NOT translated (§15.4). */
  logoAlt: 'Idéfix',
  /** Locked aspect ratio (w/h) so the mark never distorts. */
  logoAspect: '4 / 1',
  /** Minimum clear-space around the mark, in px. */
  clearSpacePx: 8,
} as const

// Signature (author attribution shown client-facing). Name is a proper noun and
// is NOT translated; the role label IS an i18n key (§15.4).
export const SIGNATURE_NAME = 'Mickaël Labarrère'
export const SIGNATURE_ROLE_KEY = 'signature.role' as const
