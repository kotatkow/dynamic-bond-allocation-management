"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  BillFrequency,
  BudgetRecommendation,
  FinancialGoal,
  IncomeClassification,
  IncomeEvent,
  RecurringBill,
  dateMonthsFromNow,
  formatKrw,
  localIsoDate,
} from "@/lib/finance";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

type DashboardData = {
  recommendation: BudgetRecommendation;
  incomes: IncomeEvent[];
  bills: RecurringBill[];
  goals: FinancialGoal[];
};

async function loadDashboardData(): Promise<DashboardData> {
  const asOf = localIsoDate();
  const [recommendation, incomes, bills, goals] = await Promise.all([
    apiRequest<BudgetRecommendation>(`/budget/recommendation?as_of=${asOf}`),
    apiRequest<IncomeEvent[]>("/incomes"),
    apiRequest<RecurringBill[]>("/recurring-bills"),
    apiRequest<FinancialGoal[]>("/goals"),
  ]);
  return { recommendation, incomes, bills, goals };
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.[0]?.msg ?? body?.detail ?? "Request failed");
  }
  return response.json() as Promise<T>;
}

export function FinanceDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setData(await loadDashboardData());
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load finance data");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadDashboardData()
      .then((loaded) => {
        if (!cancelled) {
          setData(loaded);
          setError(null);
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            requestError instanceof Error ? requestError.message : "Unable to load finance data",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(path: string, payload: Record<string, unknown>) {
    setBusy(true);
    try {
      await apiRequest(path, { method: "POST", body: JSON.stringify(payload) });
      await refresh();
      return true;
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save record");
      return false;
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <aside>
        <a className="brand" href="#top">PPI</a>
        <nav aria-label="Primary navigation">
          <a className="active" href="#overview">Overview</a>
          <a href="#income">Income</a>
          <a href="#bills">Bills</a>
          <a href="#goals">Goals</a>
        </nav>
        <p className="aside-note">Private · deterministic · local-first</p>
      </aside>

      <main id="top">
        <header className="masthead">
          <div>
            <p className="eyebrow">Personal finance · Phase 1</p>
            <h1>Portfolio Intelligence</h1>
          </div>
          <div className="as-of">As of {data?.recommendation.as_of ?? localIsoDate()}</div>
        </header>

        {error && (
          <div className="alert" role="alert">
            <strong>Connection notice</strong>
            <span>{error}. Confirm the FastAPI service is running at {API_URL}.</span>
          </div>
        )}

        <section id="overview" className="section-block">
          <SectionHeading
            number="01"
            title="Weekly spending range"
            description="A conservative range after recurring commitments and required goal funding."
          />
          <div className="recommendation-grid">
            <Metric label="Comfortable" value={data?.recommendation.comfortable_weekly} />
            <Metric label="Target" value={data?.recommendation.target_weekly} featured />
            <Metric label="Aggressive" value={data?.recommendation.aggressive_weekly} />
          </div>
          <div className="ledger-grid">
            <Metric label="Budgetable income" value={data?.recommendation.budgetable_income} detail={`${data?.recommendation.income_months_used ?? 0} observed month(s)`} compact />
            <Metric label="Recurring bills" value={data?.recommendation.recurring_bills_monthly} detail="Monthly equivalent" compact />
            <Metric label="Required goal funding" value={data?.recommendation.required_goal_contributions} detail="Deadline-aware minimum" compact />
            <Metric label="Monthly discretionary" value={data?.recommendation.sustainable_discretionary_monthly} detail="Before tier reserve" compact />
          </div>
          <div className="explanation">
            <h3>What drives this recommendation</h3>
            <ul>
              {(data?.recommendation.explanations ?? ["Add income records to begin."]).map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        </section>

        <IncomeSection incomes={data?.incomes ?? []} busy={busy} submit={submit} />
        <BillsSection bills={data?.bills ?? []} busy={busy} submit={submit} />
        <GoalsSection goals={data?.goals ?? []} busy={busy} submit={submit} />
      </main>
    </div>
  );
}

function Metric({ label, value, detail, featured = false, compact = false }: {
  label: string; value?: string; detail?: string; featured?: boolean; compact?: boolean;
}) {
  return (
    <article className={`metric ${featured ? "featured" : ""} ${compact ? "compact" : ""}`}>
      <p>{label}</p>
      <strong>{formatKrw(value ?? null)}{compact ? "" : "/week"}</strong>
      {detail && <span>{detail}</span>}
    </article>
  );
}

type Submit = (path: string, payload: Record<string, unknown>) => Promise<boolean>;

function IncomeSection({ incomes, busy, submit }: { incomes: IncomeEvent[]; busy: boolean; submit: Submit }) {
  const [classification, setClassification] = useState<IncomeClassification>("guaranteed");

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    void submit("/incomes", {
      received_date: values.get("received_date"), gross_amount: values.get("gross_amount"),
      net_amount: values.get("net_amount"), income_type: values.get("income_type"),
      source: values.get("source"), classification, notes: values.get("notes") || null,
    }).then((saved) => { if (saved) form.reset(); });
  }

  return (
    <section id="income" className="section-block">
      <SectionHeading number="02" title="Income events" description="Record actual cash flow; exceptional income never enters the baseline." />
      <div className="work-grid">
        <form onSubmit={onSubmit}>
          <h3>Add income</h3>
          <FormRow>
            <Field label="Received date"><input name="received_date" type="date" defaultValue={localIsoDate()} required /></Field>
            <Field label="Classification"><select value={classification} onChange={(event) => setClassification(event.target.value as IncomeClassification)}><option value="guaranteed">Guaranteed</option><option value="variable">Variable</option><option value="exceptional">Exceptional</option></select></Field>
          </FormRow>
          <FormRow>
            <Field label="Gross amount (KRW)"><input name="gross_amount" inputMode="numeric" pattern="[0-9]+" required /></Field>
            <Field label="Net amount (KRW)"><input name="net_amount" inputMode="numeric" pattern="[0-9]+" required /></Field>
          </FormRow>
          <FormRow>
            <Field label="Income type"><input name="income_type" placeholder="regular salary" required /></Field>
            <Field label="Source"><input name="source" placeholder="Employer" required /></Field>
          </FormRow>
          <Field label="Notes"><textarea name="notes" rows={2} /></Field>
          <button disabled={busy}>Save income event</button>
        </form>
        <RecordList empty="No income events yet.">
          {incomes.slice(0, 8).map((item) => (
            <Record key={item.id} title={item.source} value={formatKrw(item.net_amount)}>
              {item.received_date} · {item.income_type} · <span className={`tag ${item.classification}`}>{item.classification}</span>
            </Record>
          ))}
        </RecordList>
      </div>
    </section>
  );
}

function BillsSection({ bills, busy, submit }: { bills: RecurringBill[]; busy: boolean; submit: Submit }) {
  const [frequency, setFrequency] = useState<BillFrequency>("monthly");

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const paymentDay = values.get("expected_payment_day")?.toString();
    void submit("/recurring-bills", {
      name: values.get("name"), amount: values.get("amount"), category: values.get("category"),
      frequency, expected_payment_day: paymentDay ? Number(paymentDay) : null,
      essential: values.get("essential") === "on", active: true,
      effective_from: values.get("effective_from"), notes: values.get("notes") || null,
    }).then((saved) => { if (saved) form.reset(); });
  }

  return (
    <section id="bills" className="section-block">
      <SectionHeading number="03" title="Recurring bills" description="Effective dates preserve which commitments applied at a point in time." />
      <div className="work-grid">
        <form onSubmit={onSubmit}>
          <h3>Add recurring bill</h3>
          <FormRow>
            <Field label="Name"><input name="name" placeholder="Mortgage payment" required /></Field>
            <Field label="Amount (KRW)"><input name="amount" inputMode="numeric" pattern="[0-9]+" required /></Field>
          </FormRow>
          <FormRow>
            <Field label="Category"><input name="category" placeholder="housing" required /></Field>
            <Field label="Frequency"><select value={frequency} onChange={(event) => setFrequency(event.target.value as BillFrequency)}><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="annual">Annual</option></select></Field>
          </FormRow>
          <FormRow>
            <Field label="Effective from"><input name="effective_from" type="date" defaultValue={localIsoDate()} required /></Field>
            <Field label="Payment day"><input name="expected_payment_day" type="number" min="1" max="31" /></Field>
          </FormRow>
          <label className="check"><input name="essential" type="checkbox" defaultChecked /> Essential commitment</label>
          <Field label="Notes"><textarea name="notes" rows={2} /></Field>
          <button disabled={busy}>Save recurring bill</button>
        </form>
        <RecordList empty="No recurring bills yet.">
          {bills.slice(0, 8).map((item) => <Record key={item.id} title={item.name} value={formatKrw(item.amount)}>{item.frequency} · {item.category} · effective {item.effective_from}</Record>)}
        </RecordList>
      </div>
    </section>
  );
}

function GoalsSection({ goals, busy, submit }: { goals: FinancialGoal[]; busy: boolean; submit: Submit }) {
  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    void submit("/goals", {
      name: values.get("name"), target_amount: values.get("target_amount"),
      current_amount: values.get("current_amount"), target_date: values.get("target_date"),
      priority: Number(values.get("priority")), minimum_contribution: values.get("minimum_contribution") || "0",
      preferred_contribution: values.get("preferred_contribution") || "0", category: values.get("category"),
      status: "active", progress_date: localIsoDate(), notes: values.get("notes") || null,
    }).then((saved) => { if (saved) form.reset(); });
  }

  return (
    <section id="goals" className="section-block">
      <SectionHeading number="04" title="Financial goals" description="Required monthly funding is the larger of the stated minimum and the deadline pace." />
      <div className="work-grid">
        <form onSubmit={onSubmit}>
          <h3>Add financial goal</h3>
          <FormRow>
            <Field label="Name"><input name="name" placeholder="Emergency fund" required /></Field>
            <Field label="Category"><input name="category" placeholder="cash reserve" required /></Field>
          </FormRow>
          <FormRow>
            <Field label="Target amount (KRW)"><input name="target_amount" inputMode="numeric" pattern="[0-9]+" required /></Field>
            <Field label="Current amount (KRW)"><input name="current_amount" inputMode="numeric" pattern="[0-9]+" required /></Field>
          </FormRow>
          <FormRow>
            <Field label="Target date"><input name="target_date" type="date" defaultValue={dateMonthsFromNow(12)} required /></Field>
            <Field label="Priority (1 = highest)"><input name="priority" type="number" min="1" max="5" defaultValue="3" required /></Field>
          </FormRow>
          <FormRow>
            <Field label="Minimum monthly"><input name="minimum_contribution" inputMode="numeric" pattern="[0-9]+" defaultValue="0" /></Field>
            <Field label="Preferred monthly"><input name="preferred_contribution" inputMode="numeric" pattern="[0-9]+" defaultValue="0" /></Field>
          </FormRow>
          <Field label="Notes"><textarea name="notes" rows={2} /></Field>
          <button disabled={busy}>Save financial goal</button>
        </form>
        <RecordList empty="No financial goals yet.">
          {goals.map((goal) => <GoalRecord key={goal.id} goal={goal} busy={busy} submit={submit} />)}
        </RecordList>
      </div>
    </section>
  );
}

function GoalRecord({ goal, busy, submit }: { goal: FinancialGoal; busy: boolean; submit: Submit }) {
  const [amount, setAmount] = useState(goal.current_amount);
  function updateProgress(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit(`/goals/${goal.id}/progress`, { recorded_date: localIsoDate(), current_amount: amount });
  }
  return (
    <article className="record goal-record">
      <div><h4>{goal.name}</h4><p>{formatKrw(goal.current_amount)} of {formatKrw(goal.target_amount)} · due {goal.target_date} · priority {goal.priority}</p></div>
      <form className="inline-form" onSubmit={updateProgress}>
        <input aria-label={`Current amount for ${goal.name}`} value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="numeric" pattern="[0-9]+" required />
        <button disabled={busy}>Update</button>
      </form>
    </article>
  );
}

function SectionHeading({ number, title, description }: { number: string; title: string; description: string }) {
  return <div className="section-heading"><div><p className="section-number">{number}</p><h2>{title}</h2></div><p>{description}</p></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="field"><span>{label}</span>{children}</label>;
}

function FormRow({ children }: { children: React.ReactNode }) { return <div className="form-row">{children}</div>; }

function RecordList({ children, empty }: { children: React.ReactNode; empty: string }) {
  const items = Array.isArray(children) ? children : [children];
  return <div className="record-list">{items.length && items.some(Boolean) ? children : <p className="empty">{empty}</p>}</div>;
}

function Record({ title, value, children }: { title: string; value: string; children: React.ReactNode }) {
  return <article className="record"><div><h4>{title}</h4><p>{children}</p></div><strong>{value}</strong></article>;
}
