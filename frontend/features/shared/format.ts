const moneyFormatter = new Intl.NumberFormat("en-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Formats a value as "$1,250.00" with an optional trailing currency code. */
export function formatMoney(value: number | string | null | undefined, currency?: string | null) {
  const amount = Number(value ?? 0);
  const formatted = `$${moneyFormatter.format(Number.isFinite(amount) ? amount : 0)}`;
  return currency ? `${formatted} ${currency}` : formatted;
}

const dateTimeFormatter = new Intl.DateTimeFormat("en-CA", {
  weekday: "short",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

/** Formats an ISO timestamp as "Fri, Nov 13, 9:36 p.m." without seconds. */
export function formatDateTime(value: string | Date) {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? "" : dateTimeFormatter.format(date);
}

export function plural(count: number, singular: string, pluralForm = `${singular}s`) {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}
