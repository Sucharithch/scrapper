import * as React from "react"
// @ts-ignore: ESM/TypeScript import for class-variance-authority
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

// @ts-ignore: BadgeProps is compatible with children, className, and variant
function Badge({ className, variant, children, key, ...props }: BadgeProps & { children?: React.ReactNode, key?: React.Key }) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} key={key} {...props}>
      {children}
    </div>
  )
}

export { Badge, badgeVariants }
