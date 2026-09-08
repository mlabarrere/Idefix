import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

// Badge — pastille dense « style analyste ». Le variant `tone` reprend À
// L'IDENTIQUE les 6 tonalités historiques (mêmes couleurs, même base) sur la
// mécanique CVA partagée avec le reste du substrat shadcn/ui. On garde le nom
// d'export et les props (`children`, `tone`) pour ne pas toucher les sites d'appel.
const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
  {
    variants: {
      tone: {
        slate:
          "bg-gray-100 text-gray-700 ring-gray-300 dark:bg-gray-700/50 dark:text-gray-200 dark:ring-gray-600",
        gold: "bg-indigo-100 text-indigo-700 ring-indigo-300 dark:bg-indigo-500/15 dark:text-indigo-300 dark:ring-indigo-500/40",
        red: "bg-red-100 text-red-700 ring-red-300 dark:bg-red-500/15 dark:text-red-300 dark:ring-red-500/40",
        blue: "bg-sky-100 text-sky-700 ring-sky-300 dark:bg-sky-500/15 dark:text-sky-300 dark:ring-sky-500/40",
        green:
          "bg-emerald-100 text-emerald-700 ring-emerald-300 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/40",
        amber:
          "bg-amber-100 text-amber-800 ring-amber-300 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/40",
      },
    },
    defaultVariants: {
      tone: "slate",
    },
  }
)

export type BadgeTone = NonNullable<VariantProps<typeof badgeVariants>["tone"]>

function Badge({
  className,
  tone,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ tone }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
