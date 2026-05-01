import type {
  ComponentPropsWithoutRef,
  ReactNode
} from "react";

type DivProps = ComponentPropsWithoutRef<"div">;
type SectionProps = ComponentPropsWithoutRef<"section">;
type ListProps = ComponentPropsWithoutRef<"ul">;

interface LayoutPrimitiveProps {
  children: ReactNode;
  className?: string;
}

interface ListPrimitiveProps extends Omit<ListProps, "children"> {
  // ItemGrid renders a <ul>, so callers should pass <li> children. Keeping this
  // flexible for now avoids churn while making a future stricter type easy.
  children: ReactNode;
  className?: string;
}

export function PageLayout({
  children,
  className,
  ...props
}: DivProps & LayoutPrimitiveProps) {
  return (
    <div className={joinClassNames("grid gap-6", className)} {...props}>
      {children}
    </div>
  );
}

export function PageHeader({
  children,
  className,
  ...props
}: DivProps & LayoutPrimitiveProps) {
  return (
    <div
      className={joinClassNames(
        "grid gap-3 sm:flex sm:items-start sm:justify-between",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function PageActions({
  children,
  className,
  ...props
}: DivProps & LayoutPrimitiveProps) {
  return (
    <div
      className={joinClassNames("flex flex-wrap items-center gap-2", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function Panel({
  children,
  className,
  ...props
}: SectionProps & LayoutPrimitiveProps) {
  return (
    <section
      className={joinClassNames(
        "rounded-lg border border-slate-200 bg-white p-4 shadow-sm",
        className
      )}
      {...props}
    >
      {children}
    </section>
  );
}

export function ItemGrid({
  children,
  className,
  ...props
}: ListPrimitiveProps) {
  return (
    <ul
      className={joinClassNames(
        "grid gap-4 md:grid-cols-2 xl:grid-cols-3",
        className
      )}
      {...props}
    >
      {children}
    </ul>
  );
}

export function InlineCluster({
  children,
  className,
  ...props
}: DivProps & LayoutPrimitiveProps) {
  return (
    <div
      className={joinClassNames("flex flex-wrap items-center gap-2", className)}
      {...props}
    >
      {children}
    </div>
  );
}

function joinClassNames(
  ...classNames: Array<string | false | null | undefined>
): string {
  return classNames.filter(Boolean).join(" ");
}
