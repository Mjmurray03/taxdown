import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "bg-[#18181B] text-white hover:bg-[#27272A] active:bg-[#09090B] focus-visible:ring-[#18181B] transition-standard",
        secondary:
          "bg-white border border-[#E4E4E7] text-[#18181B] hover:bg-[#FAFAF9] hover:border-[#D4D4D8] active:bg-[#F4F4F5] focus-visible:ring-[#18181B] transition-standard",
        destructive:
          "bg-[#991B1B] text-white hover:bg-[#7F1D1D] focus-visible:ring-[#991B1B] transition-standard",
        ghost:
          "text-[#71717A] hover:bg-[#F4F4F5] hover:text-[#18181B] focus-visible:ring-[#18181B] transition-standard",
        link:
          "text-[#1E40AF] underline-offset-4 hover:underline focus-visible:ring-[#1E40AF]",
      },
      size: {
        default: "h-10 px-4 py-2.5 text-sm font-medium",
        sm: "h-8 rounded-md gap-1.5 px-3 text-xs font-medium",
        lg: "h-11 rounded-md px-6 text-base font-medium",
        icon: "size-10",
        "icon-sm": "size-8",
        "icon-lg": "size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
