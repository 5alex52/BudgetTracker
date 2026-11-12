import { memo } from 'react'
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  Baby,
  Banknote,
  Book,
  Box,
  Briefcase,
  Bus,
  Car,
  ChefHat,
  CircleDollarSign,
  Coffee,
  CreditCard,
  Dumbbell,
  Fuel,
  Gamepad2,
  Gift,
  GraduationCap,
  Hammer,
  Heart,
  Hospital,
  House,
  Landmark,
  Laptop,
  Leaf,
  Music,
  PawPrint,
  Percent,
  PiggyBank,
  Pill,
  Plane,
  Receipt,
  Scale,
  Shirt,
  ShoppingBag,
  ShoppingCart,
  Smartphone,
  Sparkles,
  Theater,
  Ticket,
  TrendingUp,
  Utensils,
  Wallet,
  Wrench,
  type LucideIcon,
} from 'lucide-react'

/**
 * Icon names in the demo data are strings (as in the API).
 * This is the single mapping point: only the needed icons are imported,
 * so tree-shaking is preserved.
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
  // Extended set: tech, transport, health, home, work, leisure
  coffee: Coffee,
  car: Car,
  fuel: Fuel,
  shirt: Shirt,
  smartphone: Smartphone,
  dumbbell: Dumbbell,
  plane: Plane,
  heart: Heart,
  baby: Baby,
  'paw-print': PawPrint,
  'graduation-cap': GraduationCap,
  music: Music,
  'gamepad-2': Gamepad2,
  hospital: Hospital,
  pill: Pill,
  hammer: Hammer,
  wrench: Wrench,
  briefcase: Briefcase,
  laptop: Laptop,
  percent: Percent,
  'piggy-bank': PiggyBank,
  receipt: Receipt,
  'credit-card': CreditCard,
  banknote: Banknote,
  ticket: Ticket,
  sparkles: Sparkles,
  leaf: Leaf,
}

function CategoryIconImpl({
  name,
  className,
}: {
  name: string
  className?: string
}) {
  const Icon = ICONS[name] ?? Box
  return <Icon className={className} aria-hidden="true" strokeWidth={1.75} />
}

/** Category icon: memoized — lists have dozens of them. */
export const CategoryIcon = memo(CategoryIconImpl)
