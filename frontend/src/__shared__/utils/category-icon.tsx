import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  Book,
  Box,
  Bus,
  ChefHat,
  CircleDollarSign,
  Gift,
  House,
  Landmark,
  Scale,
  ShoppingBag,
  ShoppingCart,
  Theater,
  TrendingUp,
  Utensils,
  Wallet,
  type LucideIcon,
} from 'lucide-react'

/**
 * Имена иконок в демо-данных заданы строками (как в API).
 * Здесь — единственная точка сопоставления: импортируются только нужные иконки,
 * поэтому tree-shaking сохраняется.
 */
const ICONS: Record<string, LucideIcon> = {
  utensils: Utensils,
  theater: Theater,
  'shopping-bag': ShoppingBag,
  'shopping-cart': ShoppingCart,
  bus: Bus,
  house: House,
  book: Book,
  'chef-hat': ChefHat,
  gift: Gift,
  landmark: Landmark,
  'chart-line': TrendingUp,
  box: Box,
  'arrow-down-left': ArrowDownLeft,
  'arrow-up-right': ArrowUpRight,
  'arrow-left-right': ArrowLeftRight,
  scale: Scale,
  wallet: Wallet,
  cash: CircleDollarSign,
}

export function CategoryIcon({
  name,
  className,
}: {
  name: string
  className?: string
}) {
  const Icon = ICONS[name] ?? Box
  return <Icon className={className} aria-hidden="true" strokeWidth={1.75} />
}
