import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "flex h-10 w-full rounded-md border border-[#E4E4E7] bg-white px-3 py-2 text-sm",
        "text-[#09090B] placeholder:text-[#A1A1AA]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#18181B] focus-visible:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "transition-standard",
        className
      )}
      {...props}
    />
  )
}

export { Input }
