export type IncomeClassification = "guaranteed" | "variable" | "exceptional";
export type BillFrequency = "weekly" | "monthly" | "quarterly" | "annual";

export interface IncomeEvent {
  id: string;
  received_date: string;
  gross_amount: string;
  net_amount: string;
  income_type: string;
  source: string;
  classification: IncomeClassification;
  notes: string | null;
}

export interface RecurringBill {
  id: string;
  name: string;
  amount: string;
  category: string;
  frequency: BillFrequency;
  expected_payment_day: number | null;
  essential: boolean;
  active: boolean;
  effective_from: string;
  effective_to: string | null;
}

export interface FinancialGoal {
  id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  target_date: string;
  priority: number;
  minimum_contribution: string;
  preferred_contribution: string;
  category: string;
  status: "active" | "paused" | "completed";
  latest_progress_date: string;
}

export interface BudgetRecommendation {
  as_of: string;
  budgetable_income: string;
  guaranteed_income_baseline: string;
  variable_income_baseline: string;
  lower_recent_income: string;
  income_months_used: number;
  recurring_bills_monthly: string;
  required_goal_contributions: string;
  sustainable_discretionary_monthly: string;
  comfortable_weekly: string;
  target_weekly: string;
  aggressive_weekly: string;
  previous_target_weekly: string | null;
  target_weekly_change: string | null;
  explanations: string[];
}

export function formatKrw(value: string | null): string {
  if (value === null) return "—";
  try {
    return `₩${new Intl.NumberFormat("ko-KR").format(BigInt(value))}`;
  } catch {
    return `₩${value}`;
  }
}

export function localIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function dateMonthsFromNow(months: number): string {
  const result = new Date();
  result.setMonth(result.getMonth() + months);
  const year = result.getFullYear();
  const month = String(result.getMonth() + 1).padStart(2, "0");
  const day = String(result.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
