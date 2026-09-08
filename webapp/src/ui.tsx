// Baril de primitives UI (stable). Les implémentations ont migré sur le substrat
// shadcn/ui + Radix (Phase 2B) :
//   • Badge      -> components/ui/badge      (CVA, variant `tone`)
//   • Spinner    -> components/patterns/Spinner   (lucide Loader2)
//   • EmptyState -> components/patterns/EmptyState
//   • useAsync   -> lib/useAsync
// Ce fichier ne fait plus que RÉ-EXPORTER les mêmes noms/signatures afin de
// laisser INCHANGÉS les nombreux sites d'import (`import … from '../ui'`).
export { Badge } from '@/components/ui/badge'
export { Spinner } from '@/components/patterns/Spinner'
export { EmptyState } from '@/components/patterns/EmptyState'
export { useAsync } from '@/lib/useAsync'
