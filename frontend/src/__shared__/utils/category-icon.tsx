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
  // Расширенный набор: техника, транспорт, здоровье, дом, работа, досуг
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

/** Иконка категории: мемоизирована — в списках их десятки. */
export const CategoryIcon = memo(CategoryIconImpl)
