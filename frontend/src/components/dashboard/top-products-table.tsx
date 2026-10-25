/**
 * Top Products Table — ranked list of products by revenue.
 * Includes a mini bar visualization and category badges.
 */

import { useTopProducts, type TopProduct } from '@/api/kpi'
import { formatCurrency, formatCompact, cn } from '@/lib/utils'

export function TopProductsTable() {
  const { data, isLoading, isError, error } = useTopProducts(10)

  if (isLoading) return <TableSkeleton />

  if (isError) {
    return (
      <div className="glass rounded-xl p-6">
        <h3 className="text-sm font-semibold text-foreground mb-4">Top Products</h3>
        <div className="flex h-48 items-center justify-center">
          <p className="text-sm text-critical">Failed to load: {(error as Error)?.message}</p>
        </div>
      </div>
    )
  }

  const products = data?.products ?? []
  const maxRevenue = Math.max(...products.map((p) => p.total_revenue), 1)

  if (products.length === 0) {
    return (
      <div className="glass rounded-xl p-6">
        <h3 className="text-sm font-semibold text-foreground mb-4">Top Products</h3>
        <div className="flex h-48 items-center justify-center">
          <p className="text-sm text-muted-foreground">No product data available</p>
        </div>
      </div>
    )
  }

  return (
    <div id="top-products-table" className="glass rounded-xl p-6 animate-fade-in">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Top Products by Revenue</h3>
        <span className="text-xs text-muted-foreground">Top {products.length}</span>
      </div>

      <div className="space-y-2">
        {/* Header */}
        <div className="grid grid-cols-12 gap-2 px-3 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
          <div className="col-span-1">#</div>
          <div className="col-span-4">Product</div>
          <div className="col-span-2">Category</div>
          <div className="col-span-2 text-right">Revenue</div>
          <div className="col-span-1 text-right">Qty</div>
          <div className="col-span-2" />
        </div>

        {/* Rows */}
        {products.map((product, index) => (
          <ProductRow
            key={product.product_id}
            product={product}
            rank={index + 1}
            barWidth={(product.total_revenue / maxRevenue) * 100}
          />
        ))}
      </div>
    </div>
  )
}

function ProductRow({
  product,
  rank,
  barWidth,
}: {
  product: TopProduct
  rank: number
  barWidth: number
}) {
  return (
    <div
      className={cn(
        'grid grid-cols-12 gap-2 items-center rounded-lg px-3 py-2.5 text-sm transition-colors',
        'hover:bg-accent/50',
        rank <= 3 && 'bg-primary/[0.03]',
      )}
    >
      <div className="col-span-1">
        <span
          className={cn(
            'text-xs font-bold',
            rank === 1 && 'text-amber-500 dark:text-amber-400',
            rank === 2 && 'text-slate-600 dark:text-slate-400',
            rank === 3 && 'text-amber-700 dark:text-amber-500',
            rank > 3 && 'text-muted-foreground',
          )}
        >
          {rank}
        </span>
      </div>
      <div className="col-span-4">
        <p className="text-sm font-medium text-foreground truncate" title={product.product_name}>
          {product.product_name}
        </p>
        <p className="text-xs text-muted-foreground">{product.sku}</p>
      </div>
      <div className="col-span-2">
        <span className="inline-flex items-center rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
          {product.category}
        </span>
      </div>
      <div className="col-span-2 text-right">
        <span className="text-sm font-semibold text-foreground">
          {formatCurrency(product.total_revenue)}
        </span>
      </div>
      <div className="col-span-1 text-right">
        <span className="text-xs text-muted-foreground">
          {formatCompact(product.total_qty)}
        </span>
      </div>
      <div className="col-span-2">
        <div className="h-1.5 w-full rounded-full bg-muted">
          <div
            className="h-1.5 rounded-full bg-gradient-to-r from-primary to-purple-500 transition-all duration-500"
            style={{ width: `${barWidth}%` }}
          />
        </div>
      </div>
    </div>
  )
}

function TableSkeleton() {
  return (
    <div className="glass rounded-xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="skeleton h-4 w-36" />
        <div className="skeleton h-3 w-12" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 py-2">
            <div className="skeleton h-4 w-4" />
            <div className="skeleton h-4 w-32" />
            <div className="skeleton h-4 w-16 ml-auto" />
            <div className="skeleton h-1.5 w-20 rounded-full" />
          </div>
        ))}
      </div>
    </div>
  )
}
