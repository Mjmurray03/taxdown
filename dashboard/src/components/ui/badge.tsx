import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center justify-center rounded px-2 py-1 text-xs font-medium w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 gap-1 [&>svg]:pointer-events-none transition-standard",
  {
    variants: {
      variant: {
        default:
          "bg-[#18181B] text-white",
        secondary:
          "bg-[#F4F4F5] text-[#71717A]",
        success:
          "bg-[#DCFCE7] text-[#166534]",
        warning:
          "bg-[#FEF3C7] text-[#A16207]",
        error:
          "bg-[#FEE2E2] text-[#991B1B]",
        outline:
          "border border-[#E4E4E7] bg-white text-[#09090B]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "span"

  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
