// Signature — author attribution shown client-facing (§15.4). The ONLY component
// allowed to render the signer. Name comes from brand.config (a proper noun, NOT
// translated); the role is an i18n key. Typography is subordinate by construction:
// smallest step + muted color, and it can never use the accent or a heading size.
//
// Mobile collision rule (§15.4 / §14.2): the signature must not sit inside the
// sticky bottom action bar nor the safe-area inset. Consumers place it in the
// scrollable footer; it carries a z-index below the action bar.
import { useTranslation } from 'react-i18next'
import { SIGNATURE_NAME, SIGNATURE_ROLE_KEY } from '@/brand.config'

export function Signature({ className = '' }: { className?: string }) {
  const { t } = useTranslation()
  return (
    <span
      className={`text-xs text-muted-foreground ${className}`}
      style={{ zIndex: 'var(--z-base)' }}
    >
      {SIGNATURE_NAME} — {t(SIGNATURE_ROLE_KEY)}
    </span>
  )
}
