export type View =
  | "overview"
  | "ai-quality"
  | "platform"
  | "customers"
  | "properties"
  | "jobs"
  | "files"
  | "designs"
  | "invoices"
  | "timesheets"
  | "tools";
export type OverviewWidget = "metrics" | "guide" | "recent";
export type OverviewPreferences = {
  metrics: boolean;
  guide: boolean;
  recent: boolean;
  order: OverviewWidget[];
  groupTools: boolean;
  showInvoices: boolean;
  showTimesheets: boolean;
  showTools: boolean;
  timezone: string;
  language: string;
  includeWeekends: boolean;
  timesheetNotifications: boolean;
};
export const defaultOverviewPreferences: OverviewPreferences = {
  metrics: true,
  guide: true,
  recent: true,
  order: ["metrics", "guide", "recent"],
  groupTools: true,
  showInvoices: true,
  showTimesheets: true,
  showTools: true,
  timezone: "America/Vancouver",
  language: "en-CA",
  includeWeekends: true,
  timesheetNotifications: false,
};

export const workspaceTranslations = {
  "en-CA": { overview: "Overview", customers: "Customers", properties: "Properties", jobs: "Job map", files: "File vault", designs: "Design studio", invoices: "Invoices", timesheets: "Timesheets", tools: "Field tools", more: "More tools", settings: "Settings", signOut: "Sign out", refresh: "Refresh", updated: "Workspace is up to date.", titles: { overview: "Operations overview", customers: "Customers", properties: "Properties", jobs: "Job map & directions", files: "File vault", designs: "Design studio", invoices: "Invoices", timesheets: "Timesheets", tools: "Field tools" } },
  "fr-CA": { overview: "Aperçu", customers: "Clients", properties: "Propriétés", jobs: "Carte des travaux", files: "Coffre de fichiers", designs: "Studio de conception", invoices: "Factures", timesheets: "Feuilles de temps", tools: "Outils de terrain", more: "Plus d’outils", settings: "Paramètres", signOut: "Déconnexion", refresh: "Actualiser", updated: "L’espace de travail est à jour.", titles: { overview: "Aperçu des opérations", customers: "Clients", properties: "Propriétés", jobs: "Carte et itinéraires", files: "Coffre de fichiers", designs: "Studio de conception", invoices: "Factures", timesheets: "Feuilles de temps", tools: "Outils de terrain" } },
  "it-IT": { overview: "Panoramica", customers: "Clienti", properties: "Proprietà", jobs: "Mappa lavori", files: "Archivio file", designs: "Studio progetti", invoices: "Fatture", timesheets: "Fogli ore", tools: "Strumenti", more: "Altri strumenti", settings: "Impostazioni", signOut: "Esci", refresh: "Aggiorna", updated: "L’area di lavoro è aggiornata.", titles: { overview: "Panoramica operativa", customers: "Clienti", properties: "Proprietà", jobs: "Mappa e indicazioni", files: "Archivio file", designs: "Studio progetti", invoices: "Fatture", timesheets: "Fogli ore", tools: "Strumenti" } },
  "pa-IN": { overview: "ਸੰਖੇਪ", customers: "ਗਾਹਕ", properties: "ਜਾਇਦਾਦਾਂ", jobs: "ਕੰਮ ਦਾ ਨਕਸ਼ਾ", files: "ਫਾਈਲ ਵਾਲਟ", designs: "ਡਿਜ਼ਾਈਨ ਸਟੂਡੀਓ", invoices: "ਇਨਵੌਇਸ", timesheets: "ਟਾਈਮਸ਼ੀਟਾਂ", tools: "ਫੀਲਡ ਟੂਲ", more: "ਹੋਰ ਟੂਲ", settings: "ਸੈਟਿੰਗਾਂ", signOut: "ਸਾਈਨ ਆਉਟ", refresh: "ਤਾਜ਼ਾ ਕਰੋ", updated: "ਵਰਕਸਪੇਸ ਅੱਪ ਟੂ ਡੇਟ ਹੈ।", titles: { overview: "ਕੰਮਕਾਜ ਸੰਖੇਪ", customers: "ਗਾਹਕ", properties: "ਜਾਇਦਾਦਾਂ", jobs: "ਨਕਸ਼ਾ ਅਤੇ ਰਸਤੇ", files: "ਫਾਈਲ ਵਾਲਟ", designs: "ਡਿਜ਼ਾਈਨ ਸਟੂਡੀਓ", invoices: "ਇਨਵੌਇਸ", timesheets: "ਟਾਈਮਸ਼ੀਟਾਂ", tools: "ਫੀਲਡ ਟੂਲ" } },
} as const;

export function normalizeOverviewPreferences(value: Partial<OverviewPreferences>) {
  const allowed: OverviewWidget[] = ["metrics", "guide", "recent"];
  const savedOrder = Array.isArray(value.order)
    ? value.order.filter((item): item is OverviewWidget => allowed.includes(item))
    : [];
  return {
    metrics: value.metrics ?? true,
    guide: value.guide ?? true,
    recent: value.recent ?? true,
    order: [...new Set([...savedOrder, ...allowed])],
    groupTools: value.groupTools ?? true,
    showInvoices: value.showInvoices ?? true,
    showTimesheets: value.showTimesheets ?? true,
    showTools: value.showTools ?? true,
    timezone: value.timezone ?? "America/Vancouver",
    language: value.language ?? "en-CA",
    includeWeekends: value.includeWeekends ?? true,
    timesheetNotifications: value.timesheetNotifications ?? false,
  };
}
