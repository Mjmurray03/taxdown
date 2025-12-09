import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("bg-[#F4F4F5] shimmer rounded-md", className)}
      {...props}
    />
  )
}

export { Skeleton }
