"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import QRCode from "qrcode";
import {
  Activity,
  AlertTriangle,
  Building2,
  Calculator,
  Camera,
  CheckCircle2,
  CalendarClock,
  ChevronRight,
  Ruler,
  Sparkles,
  CircleUserRound,
  ClipboardList,
  Clock3,
  Download,
  Eye,
  ArrowDown,
  ArrowUp,
  FileText,
  FolderPlus,
  FolderLock,
  Globe2,
  Gauge,
  HardDrive,
  GripVertical,
  Settings,
  ImagePlus,
  Layers,
  LayoutDashboard,
  Leaf,
  Library,
  Lock,
  LogOut,
  MapPin,
  Menu,
  Pencil,
  Plus,
  RefreshCw,
  RotateCcw,
  ReceiptText,
  ShieldCheck,
  Share2,
  SlidersHorizontal,
  Trash2,
  Users,
  Upload,
  X,
} from "lucide-react";
import { CaptureImage } from "@/features/design-studio/capture-image";
import { CameraMeasure } from "@/features/design-studio/camera-measure";
import { MaskEditor, type MaskMeasurement } from "@/features/design-studio/mask-editor";
import { MaterialEstimator } from "@/features/design-studio/material-estimator";
import { MeasuredConcept } from "@/features/design-studio/measured-concept";
import { QuoteBuilder } from "@/features/quotes/quote-builder";
import { loadWorkspaceSnapshot } from "@/features/shared/workspace-query";
import { BillingBanner, BillingSettings, type BillingState, useBilling } from "@/features/billing";
import { PriceListSettings } from "@/features/price-list";
import { type View, workspaceTranslations } from "@/features/navigation/workspace-config";
import { defaultOverviewPreferences, normalizeOverviewPreferences, type OverviewPreferences, type OverviewWidget } from "@/features/settings";
import type { InvoiceSection } from "@/features/invoices/types";
import { InvoicePayments } from "@/features/invoices/invoice-payments";
import { CustomerDetail, CustomersView } from "@/features/customers";
import { PropertyDetail, PropertiesView } from "@/features/properties";
import { JobMap, TimesheetsView } from "@/features/scheduling";
import { Empty } from "@/features/shared/empty";
import { createDemoWorkspaceAccess, demoWorkspaceAvailable } from "@/features/auth/demo-workspace";
import { NavButton } from "@/features/navigation/nav-button";
import {
  ApiError,
  Capture,
  Customer,
  CurrentUser,
  Design,
  Invoice,
  InvoiceItem,
  Organization,
  OrganizationInvitation,
  OrganizationUser,
  GenerationMetrics,
  GenerationJob,
  GenerationReview,
  PlatformOrganization,
  PlatformUser,
  Property,
  Timesheet,
  WorkOrder,
  VaultFile,
  VaultFolder,
  VaultSite,
  VaultStorage,
  apiBase,
  beginTotpEnrollment,
  confirmTotpEnrollment,
  cognitoConfirmSignUp,
  cognitoMfaToken,
  cognitoPasswordToken,
  cognitoSignUp,
  developmentToken,
  downloadAuthenticated,
  invoiceLogoBlob,
  downloadVaultFile,
  organizationLogoBlob,
  request,
} from "@/lib/api";
import { formatDateTime, formatMoney } from "@/features/shared/format";

type Composer = "customer" | "property" | "design" | null;
type EditTarget = {
  type: Exclude<Composer, null>;
  record: Customer | Property | Design;
} | null;

export default function Home() {
  const [token, setToken] = useState("");
  const [email, setEmail] = useState("");
  const [organizationId, setOrganizationId] = useState("");
  const [password, setPassword] = useState("");
  const [authScreen, setAuthScreen] = useState<
    "signin" | "register" | "workspace"
  >("signin");
  const [companyName, setCompanyName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [confirmationCode, setConfirmationCode] = useState("");
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [inviteToken, setInviteToken] = useState("");
  const [cognitoAccessToken, setCognitoAccessToken] = useState("");
  const [mfaSession, setMfaSession] = useState("");
  const [loginMfaCode, setLoginMfaCode] = useState("");
  const [pendingCognitoSession, setPendingCognitoSession] = useState<{
    idToken: string;
    accessToken: string;
  }>();
  const [view, setView] = useState<View>("overview");
  const [composer, setComposer] = useState<Composer>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [organization, setOrganization] = useState<Organization>();
  const [properties, setProperties] = useState<Property[]>([]);
  const [designs, setDesigns] = useState<Design[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [timesheets, setTimesheets] = useState<Timesheet[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [organizationUsers, setOrganizationUsers] = useState<OrganizationUser[]>([]);
  const [generationMetrics, setGenerationMetrics] = useState<GenerationMetrics>();
  const [platformOrganizations, setPlatformOrganizations] = useState<
    PlatformOrganization[]
  >([]);
  const [platformUsers, setPlatformUsers] = useState<PlatformUser[]>([]);
  const [vaultFiles, setVaultFiles] = useState<VaultFile[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser>();
  const [captures, setCaptures] = useState<Record<string, Capture[]>>({});
  const [selectedDesign, setSelectedDesign] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("");
  const [messageView, setMessageView] = useState<View | "login">("login");
  const [companyLogo, setCompanyLogo] = useState("");
  const [logoVersion, setLogoVersion] = useState(0);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer>();
  const [selectedProperty, setSelectedProperty] = useState<Property>();
  const [showWelcome, setShowWelcome] = useState(false);
  const [menuOpen, setMenuOpen] = useState(true);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<EditTarget>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { billing, refresh: refreshBilling } = useBilling(token);
  useEffect(() => {
    // Stripe redirects back with ?billing=success|cancelled|portal; confirm and tidy the URL.
    const outcome = new URLSearchParams(window.location.search).get("billing");
    if (!outcome) return;
    window.history.replaceState(null, "", window.location.pathname);
    if (outcome === "success") setMessage("Thanks — your subscription is being activated.");
    if (outcome === "cancelled") setMessage("Checkout was cancelled. Nothing was charged.");
  }, []);
  const [brandCropSource, setBrandCropSource] = useState<File>();
  const [overviewPreferences, setOverviewPreferences] =
    useState<OverviewPreferences>(defaultOverviewPreferences);

  const load = useCallback(async (activeToken: string) => {
    const snapshot = await loadWorkspaceSnapshot(activeToken);
    setOrganization(snapshot.organization);
    setCustomers(snapshot.customers);
    setProperties(snapshot.properties);
    setDesigns(snapshot.designs);
    setInvoices(snapshot.invoices);
    setTimesheets(snapshot.timesheets);
    setWorkOrders(snapshot.workOrders);
    setOrganizationUsers(snapshot.users);
    setGenerationMetrics(snapshot.generationMetrics);
    setPlatformOrganizations(snapshot.platformOrganizations);
    setPlatformUsers(snapshot.platformUsers);
    setVaultFiles(snapshot.vaultFiles);
    setCurrentUser(snapshot.currentUser);
    setSelectedDesign((current) => {
      if (!snapshot.designs.length) return undefined;
      return snapshot.designs.some((design) => design.id === current)
        ? current
        : snapshot.designs[0].id;
    });
  }, []);

  const refreshWorkspace = useCallback(async () => {
    if (refreshing) return;
    setRefreshing(true);
    setMessage("");
    try {
      await Promise.all([load(token), refreshBilling()]);
      setMessageView(view);
      const language = overviewPreferences.language as keyof typeof workspaceTranslations;
      setMessage((workspaceTranslations[language] || workspaceTranslations["en-CA"]).updated);
    } catch (caught) {
      setMessageView(view);
      setMessage(
        caught instanceof Error ? caught.message : "Refresh could not be completed.",
      );
    } finally {
      setRefreshing(false);
    }
  }, [load, overviewPreferences.language, refreshBilling, refreshing, token, view]);

  useEffect(() => {
    const invitation = new URLSearchParams(window.location.search).get("invite") || "";
    setInviteToken(invitation);
    if (invitation) setMessage("Sign in or create an account with the invited email.");
    const saved = sessionStorage.getItem("groundsops-token");
    const savedEmail = sessionStorage.getItem("groundsops-email") || "";
    const savedAccessToken =
      sessionStorage.getItem("groundsops-cognito-access") || "";
    const savedPreferences = localStorage.getItem(
      "groundsops-overview-preferences",
    );
    if (savedPreferences) {
      try {
        setOverviewPreferences(
          normalizeOverviewPreferences(JSON.parse(savedPreferences)),
        );
      } catch {
        localStorage.removeItem("groundsops-overview-preferences");
      }
    }
    if (saved) {
      setEmail(savedEmail);
      load(saved)
        .then(() => {
          setToken(saved);
          setCognitoAccessToken(savedAccessToken);
        })
        .catch(() => {
          sessionStorage.removeItem("groundsops-token");
          sessionStorage.removeItem("groundsops-email");
          sessionStorage.removeItem("groundsops-cognito-access");
          setToken("");
          setCognitoAccessToken("");
          setMessageView("login");
          setMessage("Your session could not open a workspace. Sign in again.");
        });
    }
  }, [load]);

  const openWorkspace = async (
    idToken: string,
    accessToken: string,
    acceptingInvite = false,
  ) => {
    if (acceptingInvite && inviteToken) {
      await request("/api/v1/invitations/accept", idToken, {
        method: "POST",
        body: JSON.stringify({ token: inviteToken, display_name: displayName || undefined }),
      });
      window.history.replaceState({}, "", window.location.pathname);
      setInviteToken("");
    }
    await load(idToken);
    sessionStorage.setItem("groundsops-token", idToken);
    sessionStorage.setItem("groundsops-email", email.trim());
    sessionStorage.setItem("groundsops-cognito-access", accessToken);
    setToken(idToken);
    setCognitoAccessToken(accessToken);
    setPendingCognitoSession(undefined);
    setShowWelcome(true);
    window.setTimeout(() => setShowWelcome(false), 4200);
  };

  useEffect(() => {
    if (!token || !selectedDesign || !designs.some((design) => design.id === selectedDesign))
      return;
    let active = true;
    request<Capture[]>(
      `/api/v1/design-projects/${selectedDesign}/captures`,
      token,
    )
      .then((rows) => {
        if (!active) return;
        setCaptures((current) => ({ ...current, [selectedDesign]: rows }));
      })
      .catch((error) => {
        if (!active || (error instanceof ApiError && error.status === 404)) return;
        setMessageView("designs");
        setMessage(error instanceof Error ? error.message : "Site photos could not be loaded.");
      });
    return () => { active = false; };
  }, [designs, selectedDesign, token]);

  const saveOverviewPreferences = (next: OverviewPreferences) => {
    const normalized = normalizeOverviewPreferences(next);
    setOverviewPreferences(normalized);
    localStorage.setItem(
      "groundsops-overview-preferences",
      JSON.stringify(normalized),
    );
  };

  useEffect(() => {
    if (!token || !organization?.logo_media_type) {
      setCompanyLogo("");
      return;
    }
    let objectUrl = "";
    organizationLogoBlob(token)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setCompanyLogo(objectUrl);
      })
      .catch(() => setCompanyLogo(""));
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [token, organization?.logo_media_type, logoVersion]);

  async function signIn(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessageView("login");
    setMessage("");
    try {
      let nextToken: string;
      if (process.env.NEXT_PUBLIC_AUTH_MODE === "cognito") {
        const session = mfaSession
          ? await cognitoMfaToken(email.trim(), loginMfaCode, mfaSession)
          : await cognitoPasswordToken(email.trim(), password);
        if ("challenge" in session) {
          setMfaSession(session.session);
          setMessage("Enter the six-digit code from your authenticator app.");
          return;
        }
        nextToken = session.idToken;
        setMfaSession("");
        setLoginMfaCode("");
        try {
          await openWorkspace(nextToken, session.accessToken, Boolean(inviteToken));
        } catch (workspaceError) {
          const detail =
            workspaceError instanceof Error ? workspaceError.message : "";
          if (!inviteToken && detail.includes("inactive or token is stale")) {
            setPendingCognitoSession(session);
            setAuthScreen("workspace");
            setMessage("");
            return;
          }
          throw workspaceError;
        }
        return;
      } else {
        nextToken = await developmentToken(organizationId.trim(), email.trim());
      }
      sessionStorage.setItem("groundsops-token", nextToken);
      sessionStorage.setItem("groundsops-email", email.trim());
      setToken(nextToken);
      await load(nextToken);
      setShowWelcome(true);
      window.setTimeout(() => setShowWelcome(false), 4200);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  async function openDemoWorkspace() {
    if (!demoWorkspaceAvailable()) return;
    setBusy(true);
    setMessageView("login");
    setMessage("");
    try {
      const access = await createDemoWorkspaceAccess();
      const nextToken = access.token;
      setOrganizationId(access.organizationId);
      setEmail(access.email);
      sessionStorage.setItem("groundsops-token", nextToken);
      sessionStorage.setItem("groundsops-email", access.email);
      setToken(nextToken);
      await load(nextToken);
      setShowWelcome(true);
      window.setTimeout(() => setShowWelcome(false), 4200);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Demo workspace could not be opened.");
    } finally {
      setBusy(false);
    }
  }

  async function createWorkspaceForExistingAccount(event: FormEvent) {
    event.preventDefault();
    if (!pendingCognitoSession) {
      setAuthScreen("signin");
      setMessage("Sign in again before creating your workspace.");
      return;
    }
    setBusy(true);
    setMessageView("login");
    setMessage("");
    try {
      await request("/api/v1/onboarding/register", pendingCognitoSession.idToken, {
        method: "POST",
        body: JSON.stringify({
          organization_name: companyName.trim(),
          display_name: displayName.trim(),
        }),
      });
      await openWorkspace(
        pendingCognitoSession.idToken,
        pendingCognitoSession.accessToken,
      );
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Workspace setup failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function createAccount(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessageView("login");
    setMessage("");
    try {
      if (!awaitingConfirmation) {
        await cognitoSignUp(email.trim(), password, displayName.trim());
        setAwaitingConfirmation(true);
        setMessage("Check your email for the six-digit verification code.");
        return;
      }
      await cognitoConfirmSignUp(email.trim(), confirmationCode);
      const session = await cognitoPasswordToken(email.trim(), password);
      if ("challenge" in session) {
        throw new Error("Complete MFA sign-in before finishing company setup.");
      }
      if (inviteToken) {
        await request("/api/v1/invitations/accept", session.idToken, {
          method: "POST",
          body: JSON.stringify({ token: inviteToken, display_name: displayName.trim() }),
        });
        window.history.replaceState({}, "", window.location.pathname);
        setInviteToken("");
      } else {
        await request("/api/v1/onboarding/register", session.idToken, {
          method: "POST",
          body: JSON.stringify({
            organization_name: companyName.trim(),
            display_name: displayName.trim(),
          }),
        });
      }
      await openWorkspace(session.idToken, session.accessToken);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Account setup failed.");
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    sessionStorage.removeItem("groundsops-token");
    sessionStorage.removeItem("groundsops-email");
    sessionStorage.removeItem("groundsops-cognito-access");
    setToken("");
    setCognitoAccessToken("");
    setPendingCognitoSession(undefined);
    setOrganization(undefined);
    setCustomers([]);
    setProperties([]);
    setDesigns([]);
    setInvoices([]);
    setTimesheets([]);
    setCurrentUser(undefined);
    setPlatformOrganizations([]);
    setPlatformUsers([]);
    setSelectedDesign(undefined);
    setCaptures({});
  }

  async function deleteRecord(type: Exclude<Composer, null>, id: string) {
    const linkedWarning =
      type === "customer"
        ? " Its properties, designs, captures, invoices, quotes, and work orders will also be removed."
        : type === "property"
          ? " Its designs, captures, quotes, and work orders will also be removed."
          : " Its captures and quotes will also be removed.";
    if (
      !window.confirm(
        `Delete this ${type}?${linkedWarning} This cannot be undone.`,
      )
    )
      return;
    setMessageView(view);
    setMessage("");
    try {
      const path =
        type === "customer"
          ? "customers"
          : type === "property"
            ? "properties"
            : "design-projects";
      await request(`/api/v1/${path}/${id}`, token, { method: "DELETE" });
      setSelectedCustomer(undefined);
      setSelectedProperty(undefined);
      if (type === "design") setSelectedDesign(undefined);
      await load(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Delete failed.");
    }
  }

  useEffect(() => {
    setMobileNavOpen(false);
    setMessage((current) =>
      current.trim().toLowerCase() === "not found" ? "" : current,
    );
  }, [selectedDesign, view]);

  // New company workspaces are created by GroundsOps (platform admins) and joined by invitation,
  // unless self-service sign-up is explicitly enabled for this deployment.
  const selfServiceSignup = process.env.NEXT_PUBLIC_SELF_SERVICE_SIGNUP === "true";
  const workspaceSetupBlocked = authScreen === "workspace" && !selfServiceSignup;

  if (!token) {
    return (
      <main className="login-shell">
        <section className="login-brand">
          <div className="login-brand-copy">
            <div className="login-logo">
              <div className="brand-mark animated">
                <Leaf />
              </div>
              <span>GroundsOps <b>AI</b></span>
            </div>
            <h1>Landscape design and job management, <em>in one place</em>.</h1>
            <p className="login-copy">
              Upload a site photo, mark the area to change and review an AI design concept. Then
              build the estimate, quote, schedule and invoice from the same project.
            </p>
            <ul className="login-highlights">
              <li><Sparkles /> AI edits stay inside the area you select</li>
              <li><Ruler /> Material estimates from calibrated photo measurements</li>
              <li><ShieldCheck /> Company data kept private, stored in Canada</li>
            </ul>
          </div>
          <div className="login-showcase" aria-hidden="true">
            <figure className="showcase-card before">
              <img src="/showcase/before.webp" alt="" width={683} height={513} />
              <figcaption>Before</figcaption>
            </figure>
            <figure className="showcase-card after">
              <img src="/showcase/after.webp" alt="" width={682} height={510} />
              <figcaption><Sparkles /> AI concept</figcaption>
            </figure>
          </div>
        </section>
        <section className="login-panel">
          <form
            className="login-card"
            onSubmit={
              authScreen === "register"
                ? createAccount
                : workspaceSetupBlocked
                  ? (event: FormEvent) => event.preventDefault()
                  : authScreen === "workspace"
                    ? createWorkspaceForExistingAccount
                    : signIn
            }
          >
            <div>
              <p className="eyebrow dark">
                {inviteToken
                  ? "Company invitation"
                  : authScreen === "workspace"
                    ? "Workspace setup"
                    : "GroundsOps Workspace"}
              </p>
              <h2>
                {workspaceSetupBlocked
                  ? "No workspace yet"
                  : authScreen === "workspace"
                  ? "Set up your company"
                  : authScreen === "register"
                    ? inviteToken
                      ? "Create your account"
                      : "Create your company"
                    : inviteToken
                      ? "Join your company"
                      : "Sign in to continue"}
              </h2>
              <p>
                {workspaceSetupBlocked
                  ? "This account isn't linked to a company workspace. Ask your company admin for an invitation link, or contact GroundsOps to set up a workspace."
                  : authScreen === "workspace"
                  ? "Add the business details your team will see across GroundsOps."
                  : inviteToken
                  ? "Use the exact email address that received this invitation."
                  : authScreen === "register"
                    ? "Start a secure workspace for your team."
                    : "Access your company workspace securely."}
              </p>
            </div>
            {((authScreen === "workspace" && !workspaceSetupBlocked) ||
              (authScreen === "register" && !awaitingConfirmation && !inviteToken)) && (
              <label>
                Company name
                <input required value={companyName} onChange={(event) => setCompanyName(event.target.value)} placeholder="Milan Landscaping" />
              </label>
            )}
            {((authScreen === "register" && !awaitingConfirmation) ||
              (authScreen === "workspace" && !workspaceSetupBlocked)) && (
              <label>
                Your name
                <input required value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Francesco Cheema" />
              </label>
            )}
            {process.env.NEXT_PUBLIC_AUTH_MODE !== "cognito" && (
              <label>
                Organization ID
                <input
                  required
                  value={organizationId}
                  onChange={(e) => setOrganizationId(e.target.value)}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                />
              </label>
            )}
            <label>
              Email
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@example.com"
                disabled={authScreen === "workspace"}
              />
            </label>
            {process.env.NEXT_PUBLIC_AUTH_MODE === "cognito" &&
              authScreen !== "workspace" && (
              <label>
                {authScreen === "register" && awaitingConfirmation
                  ? "Email verification code"
                  : mfaSession
                    ? "Authenticator code"
                    : "Password"}
                <input
                  required
                  type={mfaSession || awaitingConfirmation ? "text" : "password"}
                  inputMode={mfaSession || awaitingConfirmation ? "numeric" : undefined}
                  maxLength={mfaSession || awaitingConfirmation ? 6 : undefined}
                  autoComplete={
                    mfaSession ? "one-time-code" : "current-password"
                  }
                  value={awaitingConfirmation ? confirmationCode : mfaSession ? loginMfaCode : password}
                  onChange={(e) => {
                    if (awaitingConfirmation) setConfirmationCode(e.target.value.replace(/\D/g, ""));
                    else if (mfaSession) setLoginMfaCode(e.target.value.replace(/\D/g, ""));
                    else setPassword(e.target.value);
                  }}
                  placeholder={mfaSession || awaitingConfirmation ? "123456" : "At least 8 characters"}
                />
              </label>
            )}
            {message && messageView === "login" && (
              <p className="form-error" role="alert">
                {message}
              </p>
            )}
            {process.env.NEXT_PUBLIC_AUTH_MODE !== "cognito" &&
              process.env.NEXT_PUBLIC_DEMO_ORGANIZATION_ID &&
              process.env.NEXT_PUBLIC_DEMO_EMAIL && (
                <button className="demo-workspace-button" type="button" disabled={busy} onClick={() => void openDemoWorkspace()}>
                  Explore the live demo
                </button>
              )}
            {!workspaceSetupBlocked && <button className="primary" disabled={busy}>
              {busy
                ? "Working..."
                : authScreen === "workspace"
                  ? "Create company workspace"
                  : authScreen === "register" && awaitingConfirmation
                  ? inviteToken ? "Verify and join" : "Verify and create company"
                  : authScreen === "register"
                    ? "Continue"
                    : mfaSession
                  ? "Verify code"
                  : "Open workspace"}
              <ChevronRight aria-hidden="true" />
            </button>}
            {process.env.NEXT_PUBLIC_AUTH_MODE === "cognito" &&
              authScreen !== "workspace" &&
              (selfServiceSignup || inviteToken || authScreen === "register") && (
              <button
                className="auth-switch"
                type="button"
                onClick={() => {
                  setAuthScreen((current) => current === "signin" ? "register" : "signin");
                  setAwaitingConfirmation(false);
                  setConfirmationCode("");
                  setMessage("");
                }}
              >
                {authScreen === "signin"
                  ? inviteToken
                    ? "Create an account"
                    : "Create a company workspace"
                  : "Sign in to an existing workspace"}
              </button>
            )}
            {authScreen === "workspace" && (
              <button
                className="auth-switch"
                type="button"
                onClick={() => {
                  setPendingCognitoSession(undefined);
                  setAuthScreen("signin");
                  setMessage("");
                }}
              >
                Return to sign in
              </button>
            )}
            <p className="local-note">
              Secure workspace | Your token stays in this browser tab.
            </p>
            <div className="security-preview">
              <ShieldCheck />
              <span>
                <strong>Cognito account protection</strong>Email verification,
                password recovery and optional MFA are supported.
              </span>
            </div>
          </form>
        </section>
      </main>
    );
  }

  const selected = designs.find((design) => design.id === selectedDesign);
  const designCaptures = selectedDesign ? captures[selectedDesign] || [] : [];
  const propertyName = (id: string) =>
    properties.find((row) => row.id === id)?.name || "Property";
  const role = currentUser?.role || "crew";
  const managesOperations = role === "admin" || role === "manager";
  const designsWork = managesOperations || role === "designer";
  const showInvoiceNavigation =
    managesOperations && overviewPreferences.showInvoices;
  const showTimesheetNavigation = overviewPreferences.showTimesheets;
  const showFieldToolsNavigation = overviewPreferences.showTools;
  const hasToolNavigation =
    showInvoiceNavigation ||
    showTimesheetNavigation ||
    showFieldToolsNavigation;
  const groupedToolActive =
    view === "invoices" || view === "timesheets" || view === "tools";
  const copy = workspaceTranslations[
    overviewPreferences.language as keyof typeof workspaceTranslations
  ] || workspaceTranslations["en-CA"];

  async function saveBrandLogo(file: File) {
    const data = new FormData();
    data.append("file", file);
    await request("/api/v1/organization/logo", token, { method: "POST", body: data });
    setBrandCropSource(undefined);
    setLogoVersion((value) => value + 1);
    await load(token);
  }

  return (
    <main className="app-shell">
      <aside className={mobileNavOpen ? "sidebar mobile-open" : "sidebar"}>
        <div className="brand-lockup">
          {companyLogo ? (
            <img
              className="company-brand-image"
              src={companyLogo}
              alt={`${organization?.name || "Company"} logo`}
            />
          ) : (
            <div className="brand-mark small">
              <Leaf />
            </div>
          )}
          <div>
            <strong>{organization?.name || "GroundsOps"}</strong>
            <span>Powered by GroundsOps</span>
            {managesOperations && <label className="brand-replace">Change logo<input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => { setBrandCropSource(event.target.files?.[0]); event.currentTarget.value = ""; }} /></label>}
          </div>
        </div>
        <button
          type="button"
          className="mobile-navigation-toggle"
          aria-expanded={mobileNavOpen}
          aria-controls="workspace-navigation"
          onClick={() => setMobileNavOpen((open) => !open)}
        >
          <Menu />
          <span>{mobileNavOpen ? "Close menu" : "Menu"}</span>
        </button>
        <nav id="workspace-navigation" aria-label="Workspace">
          <NavButton
            active={view === "overview"}
            onClick={() => setView("overview")}
            icon={<LayoutDashboard />}
          >
            {copy.overview}
          </NavButton>
          {currentUser?.platform_admin && (
            <NavButton
              active={view === "platform"}
              onClick={() => setView("platform")}
              icon={<Building2 />}
            >
              Platform admin
            </NavButton>
          )}
          {managesOperations && (
            <NavButton
              active={view === "ai-quality"}
              onClick={() => setView("ai-quality")}
              icon={<Activity />}
            >
              AI quality
            </NavButton>
          )}
          {managesOperations && <NavButton active={view === "customers"} onClick={() => setView("customers")} icon={<Users />}>{copy.customers}</NavButton>}
          <NavButton
            active={view === "properties"}
            onClick={() => setView("properties")}
            icon={<MapPin />}
          >
            {copy.properties}
          </NavButton>
          <NavButton active={view === "jobs"} onClick={() => setView("jobs")} icon={<MapPin />}>{copy.jobs}</NavButton>
          <NavButton active={view === "files"} onClick={() => setView("files")} icon={<FolderLock />}>{copy.files}</NavButton>
          {designsWork && <NavButton
            active={view === "designs"}
            onClick={() => setView("designs")}
            icon={<Leaf className="design-leaf" />}
          >
            {copy.designs}
          </NavButton>}
          {overviewPreferences.groupTools ? (
            hasToolNavigation && (
              <>
                <button
                  className={
                    menuOpen || groupedToolActive
                      ? "nav-button menu-trigger active"
                      : "nav-button menu-trigger"
                  }
                  onClick={() => setMenuOpen((open) => !open)}
                >
                  <Menu />
                  <span>{copy.more}</span>
                </button>
                {(menuOpen || groupedToolActive) && (
                  <div className="secondary-menu">
                    {showInvoiceNavigation && (
                      <NavButton active={view === "invoices"} onClick={() => { setView("invoices"); setMenuOpen(true); }} icon={<ReceiptText />}>{copy.invoices}</NavButton>
                    )}
                    {showTimesheetNavigation && (
                      <NavButton active={view === "timesheets"} onClick={() => { setView("timesheets"); setMenuOpen(true); }} icon={<Clock3 />}>{copy.timesheets}</NavButton>
                    )}
                    {showFieldToolsNavigation && (
                      <NavButton active={view === "tools"} onClick={() => { setView("tools"); setMenuOpen(true); }} icon={<Calculator />}>{copy.tools}</NavButton>
                    )}
                  </div>
                )}
              </>
            )
          ) : (
            <>
              {showInvoiceNavigation && (
                <NavButton active={view === "invoices"} onClick={() => setView("invoices")} icon={<ReceiptText />}>{copy.invoices}</NavButton>
              )}
              {showTimesheetNavigation && (
                <NavButton active={view === "timesheets"} onClick={() => setView("timesheets")} icon={<Clock3 />}>{copy.timesheets}</NavButton>
              )}
              {showFieldToolsNavigation && (
                <NavButton active={view === "tools"} onClick={() => setView("tools")} icon={<Calculator />}>{copy.tools}</NavButton>
              )}
            </>
          )}
        </nav>
        <div className="account-area">
          <button
            className="settings-button"
            onClick={() => setSettingsOpen(true)}
            aria-label="Open settings"
          >
            <Settings />
            <span>{copy.settings}</span>
          </button>
          <button className="account" onClick={signOut}>
            <CircleUserRound />
            <span>
              <strong>{email}</strong>
              <small>
                {currentUser?.platform_admin
                  ? `Global administrator · ${copy.signOut}`
                  : copy.signOut}
              </small>
            </span>
            <LogOut />
          </button>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow dark">{organization?.name || "GroundsOps"} Workspace</p>
            <h1>
              {view === "platform"
                ? "Platform administration"
                : view === "ai-quality"
                  ? "AI quality"
                  : copy.titles[view]}
            </h1>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-button"
              onClick={() => setSettingsOpen(true)}
              aria-label="Open workspace settings"
              title={copy.settings}
            >
              <Settings />
            </button>
            <button
              className={refreshing ? "icon-button spinning" : "icon-button"}
              onClick={() => void refreshWorkspace()}
              disabled={refreshing}
              aria-label="Refresh data"
              title={copy.refresh}
            >
              <RefreshCw />
            </button>
          </div>
        </header>
        <BillingBanner billing={billing} token={token} />
        {message && message.trim().toLowerCase() !== "not found" && messageView === view && (
          <div className="notice">
            <span>{message}</span>
            <button onClick={() => setMessage("")} aria-label="Dismiss">
              <X />
            </button>
          </div>
        )}
        {showWelcome && organization && (
          <div className="welcome" role="status">
            <Leaf />
            <span>
              Welcome, <strong>{organization.name}!</strong>
            </span>
          </div>
        )}

        {view === "overview" && (
          <Overview
            customers={customers}
            properties={properties}
            designs={designs}
            role={role}
            workOrders={workOrders}
            preferences={overviewPreferences}
            onPreferencesChange={saveOverviewPreferences}
            onOpenSettings={() => setSettingsOpen(true)}
            onNavigate={setView}
            onOpenDesign={(id) => {
              setSelectedDesign(id);
              setView("designs");
            }}
          />
        )}
        {view === "platform" && currentUser?.platform_admin && (
          <PlatformAdministration
            organizations={platformOrganizations}
            users={platformUsers}
            currentUserId={currentUser.id}
            token={token}
            refresh={() => load(token)}
          />
        )}
        {view === "ai-quality" && managesOperations && (
          <AIQualityDashboard
            metrics={generationMetrics}
            onOpenDesign={(id) => {
              setSelectedDesign(id);
              setView("designs");
            }}
          />
        )}
        {view === "jobs" && <JobMap properties={properties} workOrders={workOrders} users={organizationUsers} token={token} refresh={() => load(token)} canManage={managesOperations} />}
        {view === "files" && <FileVault files={vaultFiles} token={token} refresh={() => load(token)} userId={currentUser?.id || ""} canManage={managesOperations} />}
        {view === "customers" && (
          <CustomersView
            customers={customers}
            properties={properties}
            onAdd={setComposer}
            onSelect={setSelectedCustomer}
          />
        )}
        {view === "properties" && (
          <PropertiesView
            customers={customers}
            properties={properties}
            designs={designs}
            onAdd={() => setComposer("property")}
            onSelect={setSelectedProperty}
          />
        )}
        {view === "designs" && (
          <DesignStudio
            designs={designs}
            selected={selected}
            selectedId={selectedDesign}
            setSelected={setSelectedDesign}
            propertyName={propertyName}
            propertyLocation={selected ? properties.find((property) => property.id === selected.property_id)?.location || "" : ""}
            captures={designCaptures}
            token={token}
            onAdd={() => setComposer("design")}
            onEdit={(record) => setEditTarget({ type: "design", record })}
            onDelete={(id) => deleteRecord("design", id)}
            onUploaded={() =>
              selectedDesign &&
              request<Capture[]>(
                `/api/v1/design-projects/${selectedDesign}/captures`,
                token,
              ).then((rows) =>
                setCaptures((current) => ({
                  ...current,
                  [selectedDesign]: rows,
                })),
              )
            }
            onCaptureDeleted={async () => {
              if (!selectedDesign) return;
              const rows = await request<Capture[]>(
                `/api/v1/design-projects/${selectedDesign}/captures`,
                token,
              );
              setCaptures((current) => ({
                ...current,
                [selectedDesign]: rows,
              }));
            }}
            setMessage={(value) => {
              setMessageView("designs");
              setMessage(value);
            }}
          />
        )}
        {view === "invoices" && (
          <InvoicesView
            customers={customers}
            organization={organization}
            token={token}
            invoices={invoices}
            refresh={() => load(token)}
            onLogoChanged={() => setLogoVersion((value) => value + 1)}
          />
        )}
        {view === "timesheets" && (
          <TimesheetsView
            token={token}
            properties={properties}
            entries={timesheets}
            refresh={() => load(token)}
            setMessage={(value) => {
              setMessageView("timesheets");
              setMessage(value);
            }}
            locale={overviewPreferences.language}
            timezone={overviewPreferences.timezone}
            notifications={overviewPreferences.timesheetNotifications}
            userId={currentUser?.id || ""}
            canManage={managesOperations}
          />
        )}
        {view === "tools" && <ToolsView />}
      </section>
      {composer && (
        <Composer
          type={composer}
          token={token}
          customers={customers}
          properties={properties}
          close={() => setComposer(null)}
          complete={() => {
            setComposer(null);
            load(token);
          }}
        />
      )}
      {selectedCustomer && (
        <CustomerDetail
          customer={selectedCustomer}
          properties={properties.filter(
            (row) => row.customer_id === selectedCustomer.id,
          )}
          close={() => setSelectedCustomer(undefined)}
          openProperty={(property) => {
            setSelectedCustomer(undefined);
            setSelectedProperty(property);
          }}
          edit={() =>
            setEditTarget({ type: "customer", record: selectedCustomer })
          }
          remove={() => deleteRecord("customer", selectedCustomer.id)}
        />
      )}
      {selectedProperty && (
        <PropertyDetail
          property={selectedProperty}
          customer={customers.find(
            (row) => row.id === selectedProperty.customer_id,
          )}
          designs={designs.filter(
            (row) => row.property_id === selectedProperty.id,
          )}
          close={() => setSelectedProperty(undefined)}
          openDesign={(id) => {
            setSelectedProperty(undefined);
            setSelectedDesign(id);
            setView("designs");
          }}
          edit={() =>
            setEditTarget({ type: "property", record: selectedProperty })
          }
          remove={() => deleteRecord("property", selectedProperty.id)}
        />
      )}
      {editTarget && (
        <EditRecordModal
          target={editTarget}
          token={token}
          customers={customers}
          properties={properties}
          close={() => setEditTarget(null)}
          complete={() => {
            setEditTarget(null);
            setSelectedCustomer(undefined);
            setSelectedProperty(undefined);
            load(token);
          }}
        />
      )}
      {settingsOpen && (
        <SettingsPanel
          organization={organization}
          token={token}
          cognitoAccessToken={cognitoAccessToken}
          role={role}
          platformAdmin={currentUser?.platform_admin || false}
          users={organizationUsers}
          currentUserId={currentUser?.id || ""}
          accountEmail={currentUser?.email || email}
          preferences={overviewPreferences}
          billing={billing}
          close={() => setSettingsOpen(false)}
          saved={async (next) => {
            saveOverviewPreferences(next);
            await load(token);
            setLogoVersion((value) => value + 1);
          }}
        />
      )}
      {brandCropSource && <div className="brand-editor"><LogoCropper file={brandCropSource} aspect={1} title="Edit workspace logo" description="Zoom and position the live workspace mark." cancel={() => setBrandCropSource(undefined)} apply={(file) => void saveBrandLogo(file)} /></div>}
    </main>
  );
}

function PlatformAdministration({
  organizations,
  users,
  currentUserId,
  token,
  refresh,
}: {
  organizations: PlatformOrganization[];
  users: PlatformUser[];
  currentUserId: string;
  token: string;
  refresh: () => Promise<void>;
}) {
  const [organizationId, setOrganizationId] = useState("all");
  const [accountState, setAccountState] = useState("all");
  const [status, setStatus] = useState("");
  const [busyUserId, setBusyUserId] = useState("");
  const [newCompanyName, setNewCompanyName] = useState("");
  const [newOwnerEmail, setNewOwnerEmail] = useState("");
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [workspaceLink, setWorkspaceLink] = useState("");
  const [createStatus, setCreateStatus] = useState("");
  const visibleUsers = users.filter(
    (user) =>
      (organizationId === "all" || user.organization_id === organizationId) &&
      (accountState === "all" ||
        (accountState === "active" ? user.active : !user.active)),
  );
  const activeUsers = users.filter((user) => user.active).length;

  async function setActive(user: PlatformUser, active: boolean) {
    setBusyUserId(user.id);
    setStatus("");
    try {
      await request(`/api/v1/platform/users/${user.id}/active`, token, {
        method: "PATCH",
        body: JSON.stringify({ active }),
      });
      await refresh();
      setStatus(
        active
          ? `${user.display_name} reinstated.`
          : `${user.display_name} suspended.`,
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Account update failed.");
    } finally {
      setBusyUserId("");
    }
  }

  async function createWorkspace(event: FormEvent) {
    event.preventDefault();
    setCreatingWorkspace(true);
    setCreateStatus("");
    setWorkspaceLink("");
    try {
      const created = await request<{ organization: { name: string }; invitation: { acceptance_token: string; email: string } }>(
        "/api/v1/platform/organizations",
        token,
        {
          method: "POST",
          body: JSON.stringify({ organization_name: newCompanyName.trim(), admin_email: newOwnerEmail.trim() }),
        },
      );
      const link = `${window.location.origin}${window.location.pathname}?invite=${created.invitation.acceptance_token}`;
      setWorkspaceLink(link);
      try {
        await navigator.clipboard?.writeText(link);
        setCreateStatus(`${created.organization.name} created. Invitation link for ${created.invitation.email} copied.`);
      } catch {
        setCreateStatus(`${created.organization.name} created. Copy the invitation link below.`);
      }
      setNewCompanyName("");
      setNewOwnerEmail("");
      await refresh();
    } catch (error) {
      setCreateStatus(error instanceof Error ? error.message : "Workspace could not be created.");
    } finally {
      setCreatingWorkspace(false);
    }
  }

  async function removeUser(user: PlatformUser) {
    if (
      !window.confirm(
        `Delete ${user.display_name}'s GroundsOps account? Their historical records will be preserved.`,
      )
    ) {
      return;
    }
    setBusyUserId(user.id);
    setStatus("");
    try {
      await request(`/api/v1/platform/users/${user.id}`, token, {
        method: "DELETE",
      });
      await refresh();
      setStatus(`${user.display_name}'s account was deleted.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Account deletion failed.");
    } finally {
      setBusyUserId("");
    }
  }

  return (
    <div className="platform-admin-view">
      <section className="metrics">
        <div className="metric platform-metric">
          <span className="metric-icon"><Building2 /></span>
          <span className="metric-copy"><strong>{organizations.length}</strong><small>Companies</small></span>
        </div>
        <div className="metric platform-metric">
          <span className="metric-icon"><Users /></span>
          <span className="metric-copy"><strong>{users.length}</strong><small>Total accounts</small></span>
        </div>
        <div className="metric platform-metric">
          <span className="metric-icon"><ShieldCheck /></span>
          <span className="metric-copy"><strong>{activeUsers}</strong><small>Active accounts</small></span>
        </div>
      </section>
      <section className="platform-panel">
        <div className="section-heading platform-heading">
          <div>
            <p className="eyebrow dark">New customer</p>
            <h2>Create a workspace</h2>
          </div>
        </div>
        <form className="platform-create-workspace" onSubmit={(event) => void createWorkspace(event)}>
          <label>
            Company name
            <input required minLength={2} maxLength={200} value={newCompanyName} onChange={(event) => setNewCompanyName(event.target.value)} placeholder="Cedar Landscaping" />
          </label>
          <label>
            Owner email
            <input required type="email" value={newOwnerEmail} onChange={(event) => setNewOwnerEmail(event.target.value)} placeholder="owner@company.com" />
          </label>
          <button className="primary compact" disabled={creatingWorkspace}>
            <Building2 />{creatingWorkspace ? "Creating…" : "Create and invite owner"}
          </button>
        </form>
        <p className="settings-note">The owner joins as the workspace admin through a one-time invitation link that expires in 14 days. Send it to them directly.</p>
        {createStatus && <p className="settings-status" role="status">{createStatus}</p>}
        {workspaceLink && (
          <label className="platform-invite-link">
            Invitation link
            <input readOnly value={workspaceLink} onFocus={(event) => event.currentTarget.select()} />
          </label>
        )}
      </section>
      <section className="platform-panel">
        <div className="section-heading platform-heading">
          <div>
            <p className="eyebrow dark">Platform access</p>
            <h2>Companies and users</h2>
          </div>
          <div className="platform-filters">
            <select
              aria-label="Filter by company"
              value={organizationId}
              onChange={(event) => setOrganizationId(event.target.value)}
            >
              <option value="all">All companies</option>
              {organizations.map((organization) => (
                <option value={organization.id} key={organization.id}>
                  {organization.name}
                </option>
              ))}
            </select>
            <select
              aria-label="Filter by account status"
              value={accountState}
              onChange={(event) => setAccountState(event.target.value)}
            >
              <option value="all">All accounts</option>
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
            </select>
          </div>
        </div>
        {status && <p className="settings-status" role="status">{status}</p>}
        <div className="platform-user-list">
          {visibleUsers.map((user) => (
            <div className="platform-user-row" key={user.id}>
              <span>
                <strong>{user.display_name}</strong>
                <small>{user.email} · {user.organization_name}</small>
              </span>
              <span className={`account-status ${user.active ? "active" : "suspended"}`}>
                {user.active ? "Active" : "Suspended"}
              </span>
              <span className="role-badge">
                {user.id === currentUserId ? "Global administrator" : user.role}
              </span>
              <span className="platform-user-actions">
                <button
                  className="secondary compact"
                  disabled={user.id === currentUserId || busyUserId === user.id}
                  onClick={() => void setActive(user, !user.active)}
                >
                  {busyUserId === user.id
                    ? "Updating…"
                    : user.active
                      ? "Suspend"
                      : "Reinstate"}
                </button>
                <button
                  className="danger-button compact"
                  disabled={user.id === currentUserId || busyUserId === user.id}
                  onClick={() => void removeUser(user)}
                >
                  Delete
                </button>
              </span>
            </div>
          ))}
          {!visibleUsers.length && <Empty text="No accounts match these filters." />}
        </div>
      </section>
    </div>
  );
}

const lengthUnits = {
  inch: 0.0254,
  foot: 0.3048,
  yard: 0.9144,
  metre: 1,
  centimetre: 0.01,
} as const;

function SettingsPanel({
  organization,
  token,
  cognitoAccessToken,
  role,
  platformAdmin,
  users,
  currentUserId,
  accountEmail,
  preferences,
  billing,
  close,
  saved,
}: {
  organization?: Organization;
  token: string;
  cognitoAccessToken: string;
  role: CurrentUser["role"];
  platformAdmin: boolean;
  users: OrganizationUser[];
  currentUserId: string;
  accountEmail: string;
  preferences: OverviewPreferences;
  billing?: BillingState;
  close: () => void;
  saved: (next: OverviewPreferences) => Promise<void>;
}) {
  const [name, setName] = useState(organization?.name || "");
  const [nextPreferences, setNextPreferences] = useState(preferences);
  const [secret, setSecret] = useState("");
  const [mfaQrCode, setMfaQrCode] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<OrganizationUser["role"]>("crew");
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
  const setPreference = (
    key: "metrics" | "guide" | "recent" | "groupTools" | "showInvoices" | "showTimesheets" | "showTools" | "includeWeekends" | "timesheetNotifications",
    value: boolean,
  ) =>
    setNextPreferences((current) => ({ ...current, [key]: value }));
  const movePreference = (widget: OverviewWidget, direction: -1 | 1) => {
    setNextPreferences((current) => {
      const order = [...current.order];
      const from = order.indexOf(widget);
      const to = from + direction;
      if (from < 0 || to < 0 || to >= order.length) return current;
      [order[from], order[to]] = [order[to], order[from]];
      return { ...current, order };
    });
  };
  const loadInvitations = useCallback(async () => {
    if (role !== "admin") return;
    setInvitations(await request<OrganizationInvitation[]>("/api/v1/invitations", token));
  }, [role, token]);
  useEffect(() => {
    void loadInvitations().catch(() => undefined);
  }, [loadInvitations]);
  async function inviteMember() {
    setBusy(true);
    setStatus("");
    try {
      const invitation = await request<OrganizationInvitation>("/api/v1/invitations", token, {
        method: "POST",
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      });
      const link = `${window.location.origin}${window.location.pathname}?invite=${invitation.acceptance_token}`;
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(link);
        setStatus("Invitation link copied. Send it securely to the invited person.");
      } else {
        window.prompt("Copy this invitation link", link);
        setStatus("Invitation created.");
      }
      setInviteEmail("");
      await loadInvitations();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Invitation could not be created.");
    } finally {
      setBusy(false);
    }
  }
  async function revokeInvitation(id: string) {
    try {
      await request(`/api/v1/invitations/${id}`, token, { method: "DELETE" });
      await loadInvitations();
      setStatus("Invitation revoked.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Invitation could not be revoked.");
    }
  }
  async function setMemberActive(user: OrganizationUser, active: boolean) {
    setStatus("");
    try {
      await request(`/api/v1/users/${user.id}/active`, token, {
        method: "PATCH",
        body: JSON.stringify({ active }),
      });
      await saved(nextPreferences);
      setStatus(active ? `${user.display_name} restored.` : `${user.display_name} suspended.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Member access could not be updated.");
    }
  }
  async function saveProfile() {
    setBusy(true);
    setStatus("");
    try {
      if (role === "admin" || role === "manager") {
        await request("/api/v1/organization", token, {
          method: "PUT",
          body: JSON.stringify({ name }),
        });
      }
      await saved(nextPreferences);
      setStatus("Settings saved.");
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Settings could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function startMfa() {
    try {
      setBusy(true);
      setStatus("");
      const nextSecret = await beginTotpEnrollment(cognitoAccessToken);
      const issuer = "GroundsOps AI";
      const accountLabel = `${organization?.name || "Workspace"} (${accountEmail})`;
      const label = `${issuer}:${accountLabel}`;
      const totpUri =
        `otpauth://totp/${encodeURIComponent(label)}` +
        `?secret=${encodeURIComponent(nextSecret)}` +
        `&issuer=${encodeURIComponent(issuer)}&algorithm=SHA1&digits=6&period=30`;
      const qrCode = await QRCode.toDataURL(totpUri, {
        width: 240,
        margin: 2,
        errorCorrectionLevel: "M",
        color: { dark: "#0b2a1a", light: "#ffffff" },
      });
      setSecret(nextSecret);
      setMfaQrCode(qrCode);
      setStatus(
        "Scan the QR code with your authenticator app, then enter its six-digit code.",
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "MFA setup failed.");
    } finally {
      setBusy(false);
    }
  }
  async function confirmMfa() {
    try {
      await confirmTotpEnrollment(cognitoAccessToken, mfaCode);
      setSecret("");
      setMfaQrCode("");
      setMfaCode("");
      setStatus("Authenticator MFA is enabled.");
    } catch (error) {
      setStatus(
        error instanceof Error
          ? error.message
          : "The code could not be verified.",
      );
    }
  }
  return (
    <div className="modal-backdrop">
      <section
        className="settings-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
      >
        <div className="modal-heading">
          <div>
            <p className="eyebrow dark">Workspace preferences</p>
            <h2 id="settings-title">Settings</h2>
          </div>
          <button
            className="icon-button dark"
            onClick={close}
            aria-label="Close settings"
          >
            <X />
          </button>
        </div>
        {(role === "admin" || role === "manager") && <div className="settings-section">
          <h3>Company profile</h3>
          <label>
            Company name
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
        </div>}
        <BillingSettings billing={billing} token={token} />
        {(role === "admin" || role === "manager") && <PriceListSettings token={token} canEdit />}
        {role === "admin" && <div className="settings-section">
          <h3>Team access</h3>
          <p className="settings-note">Invite employees with the minimum access they need. Invitation links expire after seven days.</p>
          <div className="team-invite-grid">
            <label>Email
              <input type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="employee@company.com" />
            </label>
            <label>Role
              <select value={inviteRole} onChange={(event) => setInviteRole(event.target.value as OrganizationUser["role"])}>
                <option value="crew">Crew</option>
                <option value="designer">Designer</option>
                <option value="manager">Manager</option>
                <option value="admin">Administrator</option>
              </select>
            </label>
            <button className="secondary" disabled={busy || !inviteEmail.trim()} onClick={inviteMember}>Invite member</button>
          </div>
          {invitations.filter((invitation) => !invitation.accepted_at && !invitation.revoked_at).map((invitation) => (
            <div className="invitation-row" key={invitation.id}>
              <span><strong>{invitation.email}</strong><small>{invitation.role} · expires {new Date(invitation.expires_at).toLocaleDateString()}</small></span>
              <button className="mini-icon-button" onClick={() => void revokeInvitation(invitation.id)} aria-label={`Revoke invitation for ${invitation.email}`}><Trash2 /></button>
            </div>
          ))}
          <div className="member-list">
            {users.map((user) => (
              <div className="invitation-row" key={user.id}>
                <span><strong>{user.display_name}</strong><small>{user.email} · {user.role}{user.active ? "" : " · suspended"}</small></span>
                <button
                  className="secondary compact"
                  disabled={user.id === currentUserId}
                  onClick={() => void setMemberActive(user, !user.active)}
                >
                  {user.active ? "Suspend" : "Reinstate"}
                </button>
              </div>
            ))}
          </div>
        </div>}
        <div className="settings-section">
          <h3>Customize overview</h3>
          <p className="settings-note">
            Show, hide or reorder the sections on your Overview.
          </p>
          {nextPreferences.order.map((widget, index) => {
            const labels: Record<OverviewWidget, string> = {
              metrics: "Summary cards",
              guide: "Field-to-concept guide",
              recent: "Recent designs",
            };
            return (
              <div className="overview-setting-row" key={widget}>
                <Toggle
                  label={labels[widget]}
                  checked={nextPreferences[widget]}
                  change={(value) => setPreference(widget, value)}
                />
                <button
                  className="mini-icon-button"
                  disabled={index === 0}
                  onClick={() => movePreference(widget, -1)}
                  aria-label={`Move ${labels[widget]} up`}
                >
                  <ArrowUp />
                </button>
                <button
                  className="mini-icon-button"
                  disabled={index === nextPreferences.order.length - 1}
                  onClick={() => movePreference(widget, 1)}
                  aria-label={`Move ${labels[widget]} down`}
                >
                  <ArrowDown />
                </button>
              </div>
            );
          })}
        </div>
        <div className="settings-section">
          <h3>Sidebar tools</h3>
          <p className="settings-note">
            Choose which tools appear and whether they stay inside More tools.
          </p>
          <Toggle
            label="Group under More tools"
            checked={nextPreferences.groupTools}
            change={(value) => setPreference("groupTools", value)}
          />
          <Toggle
            label="Invoices"
            checked={nextPreferences.showInvoices}
            change={(value) => setPreference("showInvoices", value)}
          />
          <Toggle
            label="Timesheets"
            checked={nextPreferences.showTimesheets}
            change={(value) => setPreference("showTimesheets", value)}
          />
          <Toggle
            label="Field tools"
            checked={nextPreferences.showTools}
            change={(value) => setPreference("showTools", value)}
          />
        </div>
        <div className="settings-section">
          <h3>Region and work week</h3>
          <label>Language
            <select value={nextPreferences.language} onChange={(event) => setNextPreferences((current) => ({ ...current, language: event.target.value }))}>
              <option value="en-CA">English (Canada)</option>
              <option value="fr-CA">Français (Canada)</option>
              <option value="it-IT">Italiano</option>
              <option value="pa-IN">ਪੰਜਾਬੀ</option>
            </select>
          </label>
          <label>Timezone
            <select value={nextPreferences.timezone} onChange={(event) => setNextPreferences((current) => ({ ...current, timezone: event.target.value }))}>
              <option value="America/Vancouver">Pacific Time — Vancouver</option>
              <option value="America/Edmonton">Mountain Time</option>
              <option value="America/Winnipeg">Central Time</option>
              <option value="America/Toronto">Eastern Time</option>
              <option value="UTC">UTC</option>
            </select>
          </label>
          <Toggle label="Include weekends in schedules" checked={nextPreferences.includeWeekends} change={(value) => setPreference("includeWeekends", value)} />
          <Toggle label="Timesheet start/submit notifications" checked={nextPreferences.timesheetNotifications} change={async (value) => {
            if (value && "Notification" in window) await Notification.requestPermission();
            setPreference("timesheetNotifications", value);
          }} />
        </div>
        <div className="settings-section">
          <h3>Account security</h3>
          {cognitoAccessToken ? (
            <>
              {!secret ? (
                <button className="secondary" disabled={busy} onClick={startMfa}>
                  <ShieldCheck />
                  {busy ? "Preparing QR code…" : "Set up authenticator MFA"}
                </button>
              ) : (
                <>
                  <div className="mfa-enrollment">
                    <div className="mfa-qr-frame">
                      {mfaQrCode ? (
                        <img
                          src={mfaQrCode}
                          alt="Authenticator setup QR code"
                          width={240}
                          height={240}
                        />
                      ) : (
                        <span>Preparing QR code…</span>
                      )}
                    </div>
                    <div>
                      <div className="mfa-brand">
                        <span className="mfa-brand-mark"><Leaf aria-hidden="true" /></span>
                        <span>GroundsOps AI</span>
                      </div>
                      <strong>Scan with your authenticator app</strong>
                      <p className="settings-note">
                        In Google Authenticator, Microsoft Authenticator, 1Password,
                        or another TOTP app, add an account and scan this code.
                      </p>
                    </div>
                  </div>
                  <div className="mfa-secret">
                    <span>Can’t scan it? Enter this setup key manually</span>
                    <code>{secret}</code>
                    <button
                      type="button"
                      className="text-action"
                      onClick={async () => {
                        if (navigator.clipboard?.writeText) {
                          await navigator.clipboard.writeText(secret);
                          setStatus("Authenticator setup key copied.");
                        } else {
                          window.prompt("Copy this authenticator setup key", secret);
                        }
                      }}
                    >
                      Copy setup key
                    </button>
                  </div>
                  <label>
                    Six-digit code
                    <input
                      inputMode="numeric"
                      maxLength={6}
                      value={mfaCode}
                      onChange={(event) =>
                        setMfaCode(event.target.value.replace(/\D/g, ""))
                      }
                    />
                  </label>
                  <button
                    className="secondary"
                    disabled={mfaCode.length !== 6}
                    onClick={confirmMfa}
                  >
                    Verify and enable MFA
                  </button>
                </>
              )}
            </>
          ) : (
            <p className="settings-note">
              MFA enrollment becomes available when signed in through Cognito.
            </p>
          )}
        </div>
        <div className="settings-section">
          <h3>Privacy and data</h3>
          <details className="privacy-policy">
            <summary>Privacy policy</summary>
            <p>GroundsOps stores organization records, job locations, timesheets, invoices and uploaded media for workspace operations. Access is organization-scoped and controlled by your assigned role. Site photos are sanitized to remove location metadata before storage. Administrators should only enter business information they are authorized to process.</p>
          </details>
          <p className="settings-note">
            Role: {platformAdmin ? "Global administrator" : role}.
            {!platformAdmin && " Contact your administrator to change workspace access."}
          </p>
        </div>
        {status && (
          <p className="settings-status" role="status">
            {status}
          </p>
        )}
        <div className="modal-actions">
          <button className="secondary" onClick={close}>
            Close
          </button>
          <button
            className="primary compact"
            disabled={busy || ((role === "admin" || role === "manager") && name.trim().length < 2)}
            onClick={saveProfile}
          >
            {busy ? "Saving…" : "Save settings"}
          </button>
        </div>
      </section>
    </div>
  );
}

function LogoCropper({
  file,
  aspect,
  title,
  description,
  cancel,
  apply,
  inline = false,
}: {
  file: File;
  aspect: number;
  title: string;
  description: string;
  cancel: () => void;
  apply: (file: File, preview: string) => void;
  inline?: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [image, setImage] = useState<HTMLImageElement>();
  const [zoom, setZoom] = useState(1);
  const [horizontal, setHorizontal] = useState(0);
  const [vertical, setVertical] = useState(0);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    const nextImage = new Image();
    nextImage.onload = () => setImage(nextImage);
    nextImage.src = url;
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !image) return;
    const width = 900;
    const height = Math.round(width / aspect);
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) return;
    const scale =
      Math.max(width / image.naturalWidth, height / image.naturalHeight) * zoom;
    const drawnWidth = image.naturalWidth * scale;
    const drawnHeight = image.naturalHeight * scale;
    const overflowX = Math.max(0, drawnWidth - width);
    const overflowY = Math.max(0, drawnHeight - height);
    const x = -overflowX * ((horizontal + 100) / 200);
    const y = -overflowY * ((vertical + 100) / 200);
    context.clearRect(0, 0, width, height);
    context.drawImage(image, x, y, drawnWidth, drawnHeight);
  }, [aspect, horizontal, image, vertical, zoom]);

  const finish = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (!blob) return;
      const cropped = new File([blob], "company-logo-cropped.png", {
        type: "image/png",
      });
      apply(cropped, canvas.toDataURL("image/png"));
    }, "image/png");
  };

  return (
    <div className={inline ? "crop-inline-wrap" : "crop-backdrop"} role="presentation">
      <section className={inline ? "crop-inline" : "crop-dialog"} role="dialog" aria-modal={!inline}>
        {!inline && <div className="modal-heading">
          <div>
            <p className="eyebrow dark">Logo editor</p>
            <h2>{title}</h2>
          </div>
          <button className="icon-button dark" onClick={cancel} aria-label="Close crop editor"><X /></button>
        </div>}
        <p className="crop-description">{description}</p>
        <div className={aspect === 1 ? "crop-canvas square" : "crop-canvas wide"}>
          <canvas ref={canvasRef} aria-label="Cropped logo preview" />
          <span className="crop-grid" aria-hidden="true" />
        </div>
        <div className="crop-controls">
          <label>Zoom <input type="range" min="1" max="3" step="0.01" value={zoom} onChange={(event) => setZoom(Number(event.target.value))} /></label>
          <label>Horizontal position <input type="range" min="-100" max="100" value={horizontal} onChange={(event) => setHorizontal(Number(event.target.value))} /></label>
          <label>Vertical position <input type="range" min="-100" max="100" value={vertical} onChange={(event) => setVertical(Number(event.target.value))} /></label>
        </div>
        <div className="modal-actions">
          {!inline && <button className="secondary" onClick={cancel}>Cancel</button>}
          <button className="primary compact" disabled={!image} onClick={finish}>Use this crop</button>
        </div>
      </section>
    </div>
  );
}

function Toggle({
  label,
  checked,
  change,
}: {
  label: string;
  checked: boolean;
  change: (value: boolean) => void;
}) {
  return (
    <label className="setting-toggle">
      <span>{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => change(event.target.checked)}
      />
      <i />
    </label>
  );
}

type LengthUnit = keyof typeof lengthUnits;

function ToolsView() {
  const [amount, setAmount] = useState("12");
  const [from, setFrom] = useState<LengthUnit>("foot");
  const [to, setTo] = useState<LengthUnit>("yard");
  const numeric = Number(amount);
  const converted = Number.isFinite(numeric)
    ? (numeric * lengthUnits[from]) / lengthUnits[to]
    : 0;
  return (
    <div className="tools-grid">
      <section className="section-card tool-card">
        <div className="tool-heading">
          <span className="tool-icon">
            <Calculator />
          </span>
          <div>
            <p className="eyebrow dark">Length converter</p>
            <h2>Site measurements</h2>
          </div>
        </div>
        <div className="converter">
          <label>
            Amount
            <input
              inputMode="decimal"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
            />
          </label>
          <label>
            From
            <select
              value={from}
              onChange={(event) => setFrom(event.target.value as LengthUnit)}
            >
              {Object.keys(lengthUnits).map((unit) => (
                <option key={unit} value={unit}>
                  {unit}
                </option>
              ))}
            </select>
          </label>
          <button
            className="swap"
            onClick={() => {
              setFrom(to);
              setTo(from);
            }}
            aria-label="Swap units"
          >
            ⇄
          </button>
          <label>
            To
            <select
              value={to}
              onChange={(event) => setTo(event.target.value as LengthUnit)}
            >
              {Object.keys(lengthUnits).map((unit) => (
                <option key={unit} value={unit}>
                  {unit}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="conversion-result">
          <span>
            {amount || "0"} {from}
          </span>
          <strong>
            {converted.toLocaleString(undefined, { maximumFractionDigits: 4 })}{" "}
            {to}
          </strong>
        </div>
      </section>
      <section className="section-card formula-card">
        <p className="eyebrow dark">Quick reference</p>
        <h2>Landscape conversions</h2>
        <div className="reference-grid">
          <div>
            <strong>12</strong>
            <span>inches = 1 foot</span>
          </div>
          <div>
            <strong>3</strong>
            <span>feet = 1 yard</span>
          </div>
          <div>
            <strong>27</strong>
            <span>ft³ = 1 yd³</span>
          </div>
          <div>
            <strong>10.764</strong>
            <span>ft² = 1 m²</span>
          </div>
        </div>
      </section>
      <VolumeCalculator />
    </div>
  );
}

const depthPresets = [
  { label: "Mulch", inches: 3 },
  { label: "Topsoil", inches: 4 },
  { label: "Gravel", inches: 3 },
  { label: "Paver base", inches: 6 },
];

function VolumeCalculator() {
  const [area, setArea] = useState("400");
  const [areaUnit, setAreaUnit] = useState<"ft2" | "m2">("ft2");
  const [depth, setDepth] = useState("3");
  const [preset, setPreset] = useState("Mulch");
  const [waste, setWaste] = useState("10");
  const areaFt2 = (Number(area) || 0) * (areaUnit === "m2" ? 10.7639 : 1);
  const cubicFeet = areaFt2 * ((Number(depth) || 0) / 12) * (1 + (Number(waste) || 0) / 100);
  const cubicYards = cubicFeet / 27;
  const cubicMetres = cubicFeet * 0.0283168;
  const fmt = (value: number) => value.toLocaleString("en-CA", { maximumFractionDigits: 2 });
  return (
    <section className="section-card tool-card volume-card">
      <div className="tool-heading">
        <span className="tool-icon">
          <Layers />
        </span>
        <div>
          <p className="eyebrow dark">Material volume</p>
          <h2>Order the right amount</h2>
        </div>
      </div>
      <div className="depth-presets" role="group" aria-label="Depth presets">
        {depthPresets.map((option) => (
          <button key={option.label} type="button" className={preset === option.label ? "active" : ""} aria-pressed={preset === option.label} onClick={() => { setPreset(option.label); setDepth(String(option.inches)); }}>
            {option.label} <small>{option.inches}&Prime;</small>
          </button>
        ))}
      </div>
      <div className="volume-grid">
        <label>
          Area
          <span className="input-with-unit">
            <input inputMode="decimal" value={area} onChange={(event) => setArea(event.target.value)} />
            <select aria-label="Area unit" value={areaUnit} onChange={(event) => setAreaUnit(event.target.value as "ft2" | "m2")}>
              <option value="ft2">ft²</option>
              <option value="m2">m²</option>
            </select>
          </span>
        </label>
        <label>
          Depth (inches)
          <input inputMode="decimal" value={depth} onChange={(event) => { setDepth(event.target.value); setPreset(""); }} />
        </label>
        <label>
          Waste allowance (%)
          <input inputMode="decimal" value={waste} onChange={(event) => setWaste(event.target.value)} />
        </label>
      </div>
      <div className="conversion-result volume-result">
        <span>Including {Number(waste) || 0}% waste</span>
        <strong>{fmt(cubicYards)} yd³</strong>
        <small>{fmt(cubicMetres)} m³ · {fmt(cubicFeet)} ft³</small>
      </div>
    </section>
  );
}

function InvoicesView({
  customers,
  organization,
  token,
  invoices,
  refresh,
  onLogoChanged,
}: {
  customers: Customer[];
  organization?: Organization;
  token: string;
  invoices: Invoice[];
  refresh: () => Promise<void>;
  onLogoChanged: () => void;
}) {
  const [logo, setLogo] = useState("");
  const [invoiceLogoCropSource, setInvoiceLogoCropSource] = useState<File>();
  const [customerId, setCustomerId] = useState(customers[0]?.id || "");
  const [temporaryCustomer, setTemporaryCustomer] = useState(false);
  const [saveCustomer, setSaveCustomer] = useState(false);
  const [recipientName, setRecipientName] = useState(customers[0]?.name || "");
  const [recipientEmail, setRecipientEmail] = useState(customers[0]?.email || "");
  const [recipientPhone, setRecipientPhone] = useState(customers[0]?.phone || "");
  const [recipientAddress, setRecipientAddress] = useState(customers[0]?.address || "");
  const [companyEmail, setCompanyEmail] = useState("");
  const [companyPhone, setCompanyPhone] = useState("");
  const [companyAddress, setCompanyAddress] = useState("");
  const [gstRate, setGstRate] = useState("5");
  const [pstRate, setPstRate] = useState("7");
  const [items, setItems] = useState<InvoiceItem[]>([
    {
      description: "Landscape design and site planning",
      quantity: "1",
      rate: "1250",
    },
  ]);
  const [editing, setEditing] = useState<Invoice>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [range, setRange] = useState("30");
  const [subject, setSubject] = useState("Landscaping services");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceOrder, setInvoiceOrder] = useState<InvoiceSection[]>([
    "logo", "heading", "subject", "from", "billTo", "items", "totals",
  ]);
  const [draggedInvoiceSection, setDraggedInvoiceSection] = useState<InvoiceSection>();
  useEffect(() => {
    const saved = localStorage.getItem("groundsops-invoice-layout");
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved) as InvoiceSection[];
      const allowed: InvoiceSection[] = ["logo", "heading", "subject", "from", "billTo", "items", "totals"];
      setInvoiceOrder([...new Set([...parsed.filter((item) => allowed.includes(item)), ...allowed])]);
    } catch { localStorage.removeItem("groundsops-invoice-layout"); }
  }, []);
  const subtotal = items.reduce(
    (total, item) =>
      total + (Number(item.quantity) || 0) * (Number(item.rate) || 0),
    0,
  );
  const gstAmount = subtotal * ((Number(gstRate) || 0) / 100);
  const pstAmount = subtotal * ((Number(pstRate) || 0) / 100);
  const invoiceTotal = subtotal + gstAmount + pstAmount;
  const customer = customers.find((row) => row.id === customerId);
  useEffect(() => {
    if (!organization?.invoice_logo_media_type && !organization?.logo_media_type) return;
    let url = "";
    const logoRequest = organization?.invoice_logo_media_type
      ? invoiceLogoBlob(token)
      : organizationLogoBlob(token);
    logoRequest
      .then((blob) => {
        url = URL.createObjectURL(blob);
        setLogo(url);
        setInvoiceLogoCropSource(new File([blob], "current-invoice-logo", { type: blob.type }));
      })
      .catch(() => undefined);
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [organization?.invoice_logo_media_type, organization?.logo_media_type, token]);
  async function pickLogo(file?: File) {
    if (!file) return;
    setError("");
    const reader = new FileReader();
    reader.onload = () => setLogo(String(reader.result));
    reader.readAsDataURL(file);
    const data = new FormData();
    data.append("file", file);
    try {
      await request("/api/v1/organization/invoice-logo", token, {
        method: "POST",
        body: data,
      });
      await refresh();
      onLogoChanged();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Logo upload failed.",
      );
    }
  }
  function dropInvoiceSection(target: InvoiceSection) {
    if (!draggedInvoiceSection || draggedInvoiceSection === target) return;
    const order = invoiceOrder.filter((item) => item !== draggedInvoiceSection);
    order.splice(order.indexOf(target), 0, draggedInvoiceSection);
    setInvoiceOrder(order);
    localStorage.setItem("groundsops-invoice-layout", JSON.stringify(order));
    setDraggedInvoiceSection(undefined);
  }
  function updateItem(index: number, field: keyof InvoiceItem, value: string) {
    setItems((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    );
  }
  function reset() {
    setEditing(undefined);
    setCustomerId(customers[0]?.id || "");
    setItems([{ description: "", quantity: "1", rate: "0" }]);
    setTemporaryCustomer(false);
    setSaveCustomer(false);
    const first = customers[0];
    setRecipientName(first?.name || "");
    setRecipientEmail(first?.email || "");
    setRecipientPhone(first?.phone || "");
    setRecipientAddress(first?.address || "");
    setCompanyEmail("");
    setCompanyPhone("");
    setCompanyAddress("");
    setGstRate("5");
    setPstRate("7");
    setSubject("Landscaping services");
    setInvoiceNumber("");
    setError("");
  }
  function openInvoice(invoice: Invoice) {
    const linkedCustomer = customers.find((row) => row.id === invoice.customer_id);
    setEditing(invoice);
    setCustomerId(invoice.customer_id || "");
    setTemporaryCustomer(!invoice.customer_id);
    setRecipientName(invoice.customer_name || linkedCustomer?.name || "");
    setRecipientEmail(invoice.customer_email || linkedCustomer?.email || "");
    setRecipientPhone(invoice.customer_phone || linkedCustomer?.phone || "");
    setRecipientAddress(invoice.customer_address || linkedCustomer?.address || "");
    setCompanyEmail(invoice.company_email || "");
    setCompanyPhone(invoice.company_phone || "");
    setCompanyAddress(invoice.company_address || "");
    setGstRate(invoice.gst_rate || "0");
    setPstRate(invoice.pst_rate || "0");
    setSubject(invoice.notes || "Landscaping services");
    setInvoiceNumber(invoice.number);
    setItems(invoice.items.map((item) => ({ ...item })));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  async function saveInvoice() {
    setBusy(true);
    setError("");
    const path = editing
      ? `/api/v1/invoices/${editing.id}`
      : "/api/v1/invoices";
    try {
      let savedCustomerId = temporaryCustomer ? null : customerId;
      if (temporaryCustomer && saveCustomer) {
        const created = await request<Customer>("/api/v1/customers", token, {
          method: "POST",
          body: JSON.stringify({
            name: recipientName,
            email: recipientEmail || null,
            phone: recipientPhone || null,
            address: recipientAddress || null,
          }),
        });
        savedCustomerId = created.id;
      }
      await request(path, token, {
        method: editing ? "PUT" : "POST",
        body: JSON.stringify({
          number: invoiceNumber.trim() || null,
          customer_id: savedCustomerId,
          customer_name: recipientName,
          customer_email: recipientEmail,
          customer_phone: recipientPhone,
          customer_address: recipientAddress,
          company_email: companyEmail,
          company_phone: companyPhone,
          company_address: companyAddress,
          gst_rate: Number(gstRate) || 0,
          pst_rate: Number(pstRate) || 0,
          notes: subject || null,
          items: items.map(({ description, quantity, rate }) => ({
            description,
            quantity,
            rate,
          })),
          currency: "CAD",
          status: editing?.status || "draft",
        }),
      });
      await refresh();
      reset();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Invoice could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function deleteInvoice(invoice: Invoice) {
    if (!window.confirm(`Delete ${invoice.number}? This cannot be undone.`))
      return;
    try {
      await request(`/api/v1/invoices/${invoice.id}`, token, {
        method: "DELETE",
      });
      if (editing?.id === invoice.id) reset();
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Invoice could not be deleted.",
      );
    }
  }
  const valid =
    Boolean(recipientName.trim()) &&
    items.length > 0 &&
    items.every(
      (item) =>
        Boolean(item.description.trim()) &&
        Number(item.quantity) > 0 &&
        Number(item.rate) >= 0,
    );
  const filteredInvoices = invoices.filter((invoice) =>
    range === "all"
      ? true
      : new Date(invoice.created_at).getTime() >= Date.now() - Number(range) * 86400000,
  );
  return (
    <div className="content-stack">
      <div className="invoice-layout">
        <section className="section-card invoice-editor">
          <div className="section-heading">
            <div>
              <p className="eyebrow dark">Invoice builder</p>
              <h2>{editing ? "Update invoice" : "Create an invoice"}</h2>
            </div>
            {editing && (
              <button className="secondary compact" onClick={reset}>
                New invoice
              </button>
            )}
          </div>
          <label>Invoice number<input value={invoiceNumber} onChange={(event) => setInvoiceNumber(event.target.value)} placeholder="Leave blank to generate automatically" maxLength={40} /></label>
          <label className="logo-picker">
            Company logo
            <div>
              {logo ? (
                <img src={logo} alt="Company logo preview" />
              ) : (
                <>
                  <ImagePlus />
                  <span>Choose from phone or computer</span>
                </>
              )}
            </div>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => {
                setInvoiceLogoCropSource(event.target.files?.[0]);
                event.currentTarget.value = "";
              }}
            />
          </label>
          {logo && <div className="logo-actions"><label className="secondary compact upload-inline"><ImagePlus />Replace image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => { setInvoiceLogoCropSource(event.target.files?.[0]); event.currentTarget.value = ""; }} /></label></div>}
          {invoiceLogoCropSource && (
            <LogoCropper
              file={invoiceLogoCropSource}
              aspect={12 / 5}
              title="Edit invoice logo"
              description="Zoom and position the live invoice header logo."
              cancel={() => setInvoiceLogoCropSource(undefined)}
              inline
              apply={(file) => void pickLogo(file)}
            />
          )}
          <label>Invoice subject<input value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="Landscaping services" /></label>
          <label>
            Customer source
            <select
              value={temporaryCustomer ? "__temporary__" : customerId}
              onChange={(event) => {
                const value = event.target.value;
                if (value === "__temporary__") {
                  setTemporaryCustomer(true);
                  setCustomerId("");
                  setRecipientName("");
                  setRecipientEmail("");
                  setRecipientPhone("");
                  setRecipientAddress("");
                  return;
                }
                const selectedCustomer = customers.find((row) => row.id === value);
                setTemporaryCustomer(false);
                setSaveCustomer(false);
                setCustomerId(value);
                setRecipientName(selectedCustomer?.name || "");
                setRecipientEmail(selectedCustomer?.email || "");
                setRecipientPhone(selectedCustomer?.phone || "");
                setRecipientAddress(selectedCustomer?.address || "");
              }}
            >
              <option value="">Select a customer</option>
              {customers.map((row) => (
                <option value={row.id} key={row.id}>
                  {row.name}
                </option>
              ))}
              <option value="__temporary__">+ Add customer from this invoice</option>
            </select>
          </label>
          <div className="invoice-contact-grid">
            <label>Customer name<input value={recipientName} onChange={(event) => setRecipientName(event.target.value)} /></label>
            <label>Email (optional)<input type="email" value={recipientEmail} onChange={(event) => setRecipientEmail(event.target.value)} /></label>
            <label>Phone (optional)<input value={recipientPhone} onChange={(event) => setRecipientPhone(event.target.value)} /></label>
            <label className="full-field">Address (optional)<textarea rows={2} value={recipientAddress} onChange={(event) => setRecipientAddress(event.target.value)} /></label>
          </div>
          {temporaryCustomer && (
            <Toggle
              label="Save this customer to Customers"
              checked={saveCustomer}
              change={setSaveCustomer}
            />
          )}
          <details className="invoice-options">
            <summary>Customize company details and taxes</summary>
            <div className="invoice-contact-grid">
              <label>Company email<input type="email" value={companyEmail} onChange={(event) => setCompanyEmail(event.target.value)} /></label>
              <label>Company phone<input value={companyPhone} onChange={(event) => setCompanyPhone(event.target.value)} /></label>
              <label className="full-field">Company address<textarea rows={2} value={companyAddress} onChange={(event) => setCompanyAddress(event.target.value)} /></label>
              <label>GST percentage<input type="number" min="0" max="100" step="0.001" value={gstRate} onChange={(event) => setGstRate(event.target.value)} /></label>
              <label>PST percentage<input type="number" min="0" max="100" step="0.001" value={pstRate} onChange={(event) => setPstRate(event.target.value)} /></label>
            </div>
            <p className="settings-note">Set a tax rate to 0 to remove that tax from the invoice.</p>
            <strong className="layout-title">Drag invoice sections</strong>
            <div className="invoice-layout-sorter">
              {invoiceOrder.map((section) => <button key={section} draggable="true" className={draggedInvoiceSection === section ? "dragging" : ""} onDragStart={(event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", section); setDraggedInvoiceSection(section); }} onDragEnd={() => setDraggedInvoiceSection(undefined)} onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "move"; }} onDrop={(event) => { event.preventDefault(); dropInvoiceSection(section); }}><GripVertical />{section === "billTo" ? "Bill to" : section === "heading" ? "Invoice heading" : section[0].toUpperCase() + section.slice(1)}</button>)}
            </div>
          </details>
          <div className="invoice-items-editor">
            <div className="invoice-items-title">
              <strong>Line items</strong>
              <button
                className="secondary compact"
                onClick={() =>
                  setItems((current) => [
                    ...current,
                    { description: "", quantity: "1", rate: "0" },
                  ])
                }
              >
                <Plus />
                Add item
              </button>
            </div>
            {items.map((item, index) => (
              <div className="invoice-item-edit" key={index}>
                <label>
                  Description
                  <input
                    value={item.description}
                    onChange={(event) =>
                      updateItem(index, "description", event.target.value)
                    }
                  />
                </label>
                <label>
                  Qty
                  <input
                    inputMode="decimal"
                    value={item.quantity}
                    onChange={(event) =>
                      updateItem(index, "quantity", event.target.value)
                    }
                  />
                </label>
                <label>
                  Rate
                  <input
                    inputMode="decimal"
                    value={item.rate}
                    onChange={(event) =>
                      updateItem(index, "rate", event.target.value)
                    }
                  />
                </label>
                <button
                  className="remove-item"
                  disabled={items.length === 1}
                  onClick={() =>
                    setItems((current) =>
                      current.filter((_, itemIndex) => itemIndex !== index),
                    )
                  }
                  aria-label="Remove line item"
                >
                  <Trash2 />
                </button>
              </div>
            ))}
          </div>
          {error && <p className="form-error">{error}</p>}
          <div className="invoice-editor-actions">
            <button
              className="primary"
              disabled={busy || !valid}
              onClick={saveInvoice}
            >
              <FileText />
              {busy ? "Saving…" : editing ? "Save changes" : "Save invoice"}
            </button>
            <button
              className="secondary"
              type="button"
              onClick={() => window.print()}
            >
              <Download /> Save PDF
            </button>
          </div>
        </section>
        <section className="invoice-paper">
          <div draggable className="invoice-logo-block invoice-draggable" style={{ order: invoiceOrder.indexOf("logo") + 1 }} onDragStart={() => setDraggedInvoiceSection("logo")} onDragOver={(event) => event.preventDefault()} onDrop={() => dropInvoiceSection("logo")}><GripVertical />
            {logo ? (
              <img src={logo} alt="" />
            ) : (
              <div className="invoice-logo">
                <Leaf />
              </div>
            )}
          </div>
          <div draggable className="invoice-heading invoice-draggable" style={{ order: invoiceOrder.indexOf("heading") + 1 }} onDragStart={() => setDraggedInvoiceSection("heading")} onDragOver={(event) => event.preventDefault()} onDrop={() => dropInvoiceSection("heading")}><GripVertical />
              <p>INVOICE</p>
              <strong>{invoiceNumber || editing?.number || "Auto-generated"}</strong>
          </div>
          {subject && <div draggable className="invoice-subject invoice-draggable" style={{ order: invoiceOrder.indexOf("subject") + 1 }} onDragStart={(event) => { event.dataTransfer.setData("text/plain", "subject"); setDraggedInvoiceSection("subject"); }} onDragOver={(event) => event.preventDefault()} onDrop={() => dropInvoiceSection("subject")}><GripVertical /><span>Subject</span><strong>{subject}</strong></div>}
          <div draggable className="invoice-party invoice-draggable" style={{ order: invoiceOrder.indexOf("from") + 1 }} onDragStart={() => setDraggedInvoiceSection("from")} onDragOver={(event) => event.preventDefault()} onDrop={() => dropInvoiceSection("from")}><GripVertical />
              <span>From</span>
              <strong>{organization?.name || "Your company"}</strong>
              {companyAddress && <small>{companyAddress}</small>}
              {companyEmail && <small>{companyEmail}</small>}
              {companyPhone && <small>{companyPhone}</small>}
          </div>
          <div draggable className="invoice-party invoice-draggable" style={{ order: invoiceOrder.indexOf("billTo") + 1 }} onDragStart={() => setDraggedInvoiceSection("billTo")} onDragOver={(event) => event.preventDefault()} onDrop={() => dropInvoiceSection("billTo")}><GripVertical />
              <span>Bill to</span>
              <strong>{recipientName || customer?.name || "Add a customer"}</strong>
              {recipientAddress && <small>{recipientAddress}</small>}
              {recipientEmail && <small>{recipientEmail}</small>}
              {recipientPhone && <small>{recipientPhone}</small>}
          </div>
          <div draggable className="invoice-lines invoice-draggable" style={{ order: invoiceOrder.indexOf("items") + 1 }} onDragStart={(event) => { event.dataTransfer.setData("text/plain", "items"); setDraggedInvoiceSection("items"); }} onDragOver={(event) => event.preventDefault()} onDrop={() => dropInvoiceSection("items")}><GripVertical />{items.map((item, index) => (
            <div className="invoice-line" key={index}>
              <span>{item.description || "Service"}</span>
              <span>
                {item.quantity || 0} × {formatMoney(item.rate)}
              </span>
              <strong>
                $
                {(
                  (Number(item.quantity) || 0) * (Number(item.rate) || 0)
                ).toFixed(2)}
              </strong>
            </div>
          ))}</div>
          <footer draggable className="invoice-draggable" style={{ order: invoiceOrder.indexOf("totals") + 1 }} onDragStart={(event) => { event.dataTransfer.setData("text/plain", "totals"); setDraggedInvoiceSection("totals"); }} onDragOver={(event) => event.preventDefault()} onDrop={() => dropInvoiceSection("totals")}><GripVertical />
            <div><span>Subtotal</span><strong>{formatMoney(subtotal, "CAD")}</strong></div>
            {Number(gstRate) > 0 && <div><span>GST ({Number(gstRate)}%)</span><strong>{formatMoney(gstAmount)}</strong></div>}
            {Number(pstRate) > 0 && <div><span>PST ({Number(pstRate)}%)</span><strong>{formatMoney(pstAmount)}</strong></div>}
            <div className="invoice-total"><span>Total</span><strong>{formatMoney(invoiceTotal, "CAD")}</strong></div>
          </footer>
        </section>
      </div>
      <section className="section-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow dark">Saved records</p>
            <h2>Invoice history</h2>
          </div>
          <select className="range-select" value={range} onChange={(event) => setRange(event.target.value)} aria-label="Invoice time range">
            <option value="7">Last 7 days</option><option value="30">Last month</option><option value="365">Last year</option><option value="all">All time</option>
          </select>
        </div>
        {filteredInvoices.length ? (
          <div className="timesheet-table">
            <div className="invoice-history-head">
              <span>Invoice</span>
              <span>Customer</span>
              <span>Status</span>
              <span>Total</span>
              <span>Actions</span>
            </div>
            {filteredInvoices.map((invoice) => (
              <div className="invoice-history-row" key={invoice.id}>
                <button
                  className="invoice-link"
                  onClick={() => openInvoice(invoice)}
                >
                  <strong>{invoice.number}</strong>
                </button>
                <span>
                  {customers.find((row) => row.id === invoice.customer_id)
                    ?.name || invoice.customer_name || "Customer"}
                </span>
                <span className="status-text">{invoice.status}</span>
                <strong>
                  {formatMoney(invoice.total || invoice.subtotal, invoice.currency)}
                </strong>
                <div className="row-actions">
                  <button
                    onClick={() => openInvoice(invoice)}
                    aria-label={`Edit ${invoice.number}`}
                  >
                    <Pencil />
                  </button>
                  <button
                    className="danger"
                    onClick={() => deleteInvoice(invoice)}
                    aria-label={`Delete ${invoice.number}`}
                  >
                    <Trash2 />
                  </button>
                </div>
                <InvoicePayments invoice={invoice} token={token} refresh={refresh} />
              </div>
            ))}
          </div>
        ) : (
          <Empty text="No invoices were found in this time range." />
        )}
      </section>
    </div>
  );
}

function FileVault({ files, token, refresh, userId, canManage }: { files: VaultFile[]; token: string; refresh: () => Promise<void>; userId: string; canManage: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [deletedFiles, setDeletedFiles] = useState<VaultFile[]>([]);
  const [deletedFolders, setDeletedFolders] = useState<VaultFolder[]>([]);
  const [deletedSites, setDeletedSites] = useState<VaultSite[]>([]);
  const [preview, setPreview] = useState<{ file: VaultFile; url: string }>();
  const [uploadScope, setUploadScope] = useState<"organization" | "management" | "private">("organization");
  const [folders, setFolders] = useState<VaultFolder[]>([]);
  const [sites, setSites] = useState<VaultSite[]>([]);
  const [siteFolders, setSiteFolders] = useState<VaultFolder[]>([]);
  const [storage, setStorage] = useState<VaultStorage>();
  const [section, setSection] = useState<"files" | "sites" | "recycle">("files");
  const [folderId, setFolderId] = useState("");
  const [siteId, setSiteId] = useState("");
  const [containedFiles, setContainedFiles] = useState<VaultFile[]>([]);
  const recycle = section === "recycle";
  const visibleFiles = recycle
    ? deletedFiles
    : folderId || siteId
      ? containedFiles
      : files;

  useEffect(() => () => {
    if (preview?.url) URL.revokeObjectURL(preview.url);
  }, [preview]);

  const loadVaultNavigation = useCallback(async () => {
    const [folderRows, siteRows, storageRow] = await Promise.all([
      request<VaultFolder[]>("/api/v1/vault/folders", token),
      request<VaultSite[]>("/api/v1/vault/sites", token),
      request<VaultStorage>("/api/v1/vault/storage", token),
    ]);
    setFolders(folderRows);
    setSites(siteRows);
    setStorage(storageRow);
  }, [token]);

  useEffect(() => {
    void loadVaultNavigation();
  }, [loadVaultNavigation]);

  async function openContainer(kind: "folder" | "site", id: string) {
    setFolderId(kind === "folder" ? id : "");
    const parentSite = kind === "folder"
      ? [...folders, ...siteFolders].find((folder) => folder.id === id)?.site_id || ""
      : id;
    setSiteId(parentSite);
    setSection("files");
    setContainedFiles(
      await request<VaultFile[]>(
        `/api/v1/vault/files?${kind}_id=${encodeURIComponent(id)}`,
        token,
      ),
    );
    if (kind === "site") {
      setSiteFolders(
        await request<VaultFolder[]>(
          `/api/v1/vault/folders?site_id=${encodeURIComponent(id)}`,
          token,
        ),
      );
    }
  }

  async function createFolder() {
    const name = window.prompt("Folder name")?.trim();
    if (!name) return;
    await request("/api/v1/vault/folders", token, {
      method: "POST", body: JSON.stringify({ name, site_id: siteId || null }),
    });
    await loadVaultNavigation();
    if (siteId) {
      setSiteFolders(
        await request<VaultFolder[]>(
          `/api/v1/vault/folders?site_id=${encodeURIComponent(siteId)}`,
          token,
        ),
      );
    }
  }

  async function createSite() {
    const name = window.prompt("Site name")?.trim();
    if (!name) return;
    const description = window.prompt("Short site description (optional)")?.trim() || null;
    await request("/api/v1/vault/sites", token, {
      method: "POST", body: JSON.stringify({ name, description }),
    });
    await loadVaultNavigation();
    setSection("sites");
  }

  async function loadRecycle() {
    const [fileRows, folderRows, siteRows] = await Promise.all([
      request<VaultFile[]>("/api/v1/vault/files?recycle_bin=true", token),
      request<VaultFolder[]>("/api/v1/vault/folders?recycle_bin=true", token),
      request<VaultSite[]>("/api/v1/vault/sites?recycle_bin=true", token),
    ]);
    setDeletedFiles(fileRows);
    setDeletedFolders(folderRows);
    setDeletedSites(siteRows);
  }
  async function refreshVaultView() {
    await Promise.all([refresh(), loadVaultNavigation()]);
    if (folderId) await openContainer("folder", folderId);
    else if (siteId) await openContainer("site", siteId);
  }
  async function upload(file?: File) {
    if (!file) return;
    setBusy(true);
    setError("");
    const data = new FormData();
    data.append("file", file);
    if (folderId) data.append("folder_id", folderId);
    if (siteId) data.append("site_id", siteId);
    try {
      const saved = await request<VaultFile>("/api/v1/vault/files", token, {
        method: "POST", body: data,
      });
      if (uploadScope === "private") {
        await request(`/api/v1/vault/files/${saved.id}/access`, token, {
          method: "PUT", body: JSON.stringify({ access_scope: "private" }),
        });
      }
      await refresh();
      await loadVaultNavigation();
      if (folderId) await openContainer("folder", folderId);
      if (siteId) await openContainer("site", siteId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }
  async function download(file: VaultFile) {
    const blob = await downloadVaultFile(file.id, token);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = file.original_filename;
    link.click();
    URL.revokeObjectURL(url);
  }
  async function openPreview(file: VaultFile) {
    const safe = file.media_type === "application/pdf" || file.media_type === "text/plain" || (file.media_type.startsWith("image/") && file.media_type !== "image/svg+xml");
    if (!safe) return void download(file);
    const blob = await downloadVaultFile(file.id, token, true);
    setPreview({ file, url: URL.createObjectURL(blob) });
  }
  async function rename(file: VaultFile) {
    const name = window.prompt("Rename file", file.original_filename)?.trim();
    if (!name || name === file.original_filename) return;
    await request(`/api/v1/vault/files/${file.id}/name`, token, {
      method: "PUT", body: JSON.stringify({ name }),
    });
    await refreshVaultView();
  }
  async function toggleAccess(file: VaultFile) {
    const scopes: VaultFile["access_scope"][] = canManage
      ? ["organization", "management", "private"]
      : ["organization", "private"];
    const currentIndex = scopes.indexOf(file.access_scope);
    const access_scope = scopes[(currentIndex + 1) % scopes.length];
    await request(`/api/v1/vault/files/${file.id}/access`, token, {
      method: "PUT", body: JSON.stringify({ access_scope }),
    });
    await refreshVaultView();
  }
  async function copyLink(link: string) {
    try {
      if (navigator.clipboard?.writeText && window.isSecureContext) {
        await navigator.clipboard.writeText(link);
        setError("Secure seven-day link copied to clipboard.");
        return;
      }
    } catch { /* use the visible fallback below */ }
    window.prompt("Copy this secure seven-day link", link);
  }
  async function share(file: VaultFile) {
    const result = await request<{ url_token: string }>(`/api/v1/vault/files/${file.id}/shares`, token, {
      method: "POST", body: JSON.stringify({ expires_in_hours: 168 }),
    });
    const link = `${apiBase()}/api/v1/vault/shared/${result.url_token}`;
    let copied = false;
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(link);
        copied = true;
      } catch {
        copied = false;
      }
    }
    if (!copied) {
      const textArea = document.createElement("textarea");
      textArea.value = link;
      textArea.style.position = "fixed";
      textArea.style.opacity = "0";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      copied = document.execCommand("copy");
      textArea.remove();
    }
    if (!copied) {
      window.prompt("Copy this secure seven-day share link", link);
    }
    setError(
      copied
        ? "Secure seven-day view link copied to clipboard."
        : "Share link created. Copy it from the dialog.",
    );
  }
  async function remove(file: VaultFile) {
    if (!confirm(`Move ${file.original_filename} to the recycle bin?`)) return;
    await request(`/api/v1/vault/files/${file.id}`, token, { method: "DELETE" });
    await refreshVaultView();
  }
  async function restore(file: VaultFile) {
    await request(`/api/v1/vault/files/${file.id}/restore`, token, { method: "POST" });
    await Promise.all([refresh(), loadRecycle()]);
  }
  async function erase(file: VaultFile) {
    if (!confirm(`Permanently delete ${file.original_filename}? This cannot be undone.`)) return;
    await request(`/api/v1/vault/files/${file.id}/permanent`, token, { method: "DELETE" });
    await loadRecycle();
  }
  const mayEdit = (file: VaultFile) => canManage || file.uploaded_by_user_id === userId;
  type Container = VaultFolder | VaultSite;
  async function downloadContainer(kind: "folders" | "sites", item: Container) {
    const blob = await downloadAuthenticated(`/api/v1/vault/containers/${kind}/${item.id}/download`, token);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${item.name}.zip`;
    link.click();
    URL.revokeObjectURL(url);
  }
  async function renameContainer(kind: "folders" | "sites", item: Container) {
    const name = window.prompt(`Rename ${kind === "folders" ? "folder" : "site"}`, item.name)?.trim();
    if (!name || name === item.name) return;
    await request(`/api/v1/vault/containers/${kind}/${item.id}/name`, token, {
      method: "PUT", body: JSON.stringify({ name }),
    });
    await loadVaultNavigation();
  }
  async function accessContainer(kind: "folders" | "sites", item: Container) {
    const scopes: Container["access_scope"][] = ["organization", "management", "private"];
    const access_scope = scopes[(scopes.indexOf(item.access_scope) + 1) % scopes.length];
    await request(`/api/v1/vault/containers/${kind}/${item.id}/access`, token, {
      method: "PUT", body: JSON.stringify({ access_scope }),
    });
    setError(`Access changed to ${access_scope}.`);
    await loadVaultNavigation();
  }
  async function shareContainer(kind: "folders" | "sites", item: Container) {
    const result = await request<{ url_token: string }>(
      `/api/v1/vault/containers/${kind}/${item.id}/shares`, token,
      { method: "POST", body: JSON.stringify({ expires_in_hours: 168 }) },
    );
    await copyLink(`${apiBase()}/api/v1/vault/shared-container/${result.url_token}`);
  }
  async function recycleContainer(kind: "folders" | "sites", item: Container) {
    if (!confirm(`Move ${item.name} and its files to the recycle bin?`)) return;
    await request(`/api/v1/vault/containers/${kind}/${item.id}`, token, { method: "DELETE" });
    await loadVaultNavigation();
  }
  async function restoreContainer(kind: "folders" | "sites", item: Container) {
    await request(`/api/v1/vault/containers/${kind}/${item.id}/restore`, token, { method: "POST" });
    await Promise.all([loadVaultNavigation(), loadRecycle(), refresh()]);
  }
  async function eraseContainer(kind: "folders" | "sites", item: Container) {
    if (!confirm(`Permanently delete ${item.name} and every file inside it?`)) return;
    await request(`/api/v1/vault/containers/${kind}/${item.id}/permanent`, token, { method: "DELETE" });
    await Promise.all([loadRecycle(), refresh()]);
  }
  function containerCard(kind: "folders" | "sites", item: Container) {
    const openKind = kind === "folders" ? "folder" : "site";
    return <article className="vault-container" key={`${kind}-${item.id}`}>
      <button className="vault-container-open" onClick={() => void openContainer(openKind, item.id)}>
        {kind === "folders" ? <FolderPlus /> : <Library />}
        <span><strong>{item.name}</strong><small>{kind === "folders" ? "Folder" : (item as VaultSite).description || "Team site"}</small></span>
        <ChevronRight />
      </button>
      {canManage && <div className="vault-container-actions">
        <button onClick={() => void downloadContainer(kind, item)} title="Download as ZIP"><Download /></button>
        <button onClick={() => void renameContainer(kind, item)} title="Rename"><Pencil /></button>
        <button onClick={() => void accessContainer(kind, item)} title={`Access: ${item.access_scope}`}><Lock /></button>
        <button onClick={() => void shareContainer(kind, item)} title="Share"><Share2 /></button>
        <button className="danger" onClick={() => void recycleContainer(kind, item)} title="Recycle"><Trash2 /></button>
      </div>}
    </article>;
  }
  return (
    <div className="content-stack vault-page">
      <section className="vault-hero">
        <div><p className="eyebrow">Internal files</p><h2>Work together, without losing control.</h2><p>Preview, organize and securely share company documents.</p></div>
        <div className="vault-upload-controls">
          <label className="vault-scope-picker"><span>Who can open this?</span><select value={uploadScope} onChange={(event) => setUploadScope(event.target.value as "organization" | "management" | "private")} aria-label="Who can open uploaded files"><option value="organization">Everyone in company</option>{canManage && <option value="management">Admins and managers</option>}<option value="private">Only me</option></select></label>
          <button className="secondary vault-new-button" onClick={() => void createFolder()}><FolderPlus />New folder</button>
          {canManage && <button className="secondary vault-new-button" onClick={() => void createSite()}><Library />New site</button>}
          <label className="primary"><Upload />{busy ? "Uploading…" : "Upload file"}<input type="file" disabled={busy} onChange={(event) => void upload(event.target.files?.[0])} /></label>
        </div>
      </section>
      {storage && <section className="vault-storage"><HardDrive /><div><strong>Workspace storage</strong><span>{(storage.used_bytes / 1048576).toFixed(1)} MB used · {(storage.available_bytes / 1073741824).toFixed(2)} GB available</span><div><i style={{ width: `${Math.min(100, storage.used_bytes / storage.quota_bytes * 100)}%` }} /></div></div></section>}
      {error && <div className="vault-toast">{error}<button onClick={() => setError("")}><X /></button></div>}
      <section className="section-card vault-drop" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); void upload(event.dataTransfer.files[0]); }}>
        <div className="section-heading"><div><p className="eyebrow dark">Company vault</p><h2>{recycle ? "Recycle bin" : folderId ? [...folders, ...siteFolders].find((folder) => folder.id === folderId)?.name : siteId ? sites.find((site) => site.id === siteId)?.name : section === "sites" ? "Team sites" : "My files"}</h2>{(folderId || siteId) && <button className="vault-back" onClick={() => { if (folderId && siteId) { void openContainer("site", siteId); } else { setFolderId(""); setSiteId(""); setContainedFiles([]); } }}>{folderId && siteId ? "← Back to site" : "← All files"}</button>}</div><div className="vault-tabs"><button className={section === "files" ? "active" : ""} onClick={() => { setSection("files"); setFolderId(""); setSiteId(""); }}><FolderLock />Files</button><button className={section === "sites" ? "active" : ""} onClick={() => { setSection("sites"); setFolderId(""); setSiteId(""); }}><Library />Sites</button><button className={recycle ? "active" : ""} onClick={() => { setSection("recycle"); void loadRecycle(); }}><Trash2 />Recycle bin</button></div></div>
        {section === "files" && !folderId && !siteId && folders.length > 0 && <div className="vault-folders">{folders.map((folder) => containerCard("folders", folder))}</div>}
        {section === "files" && siteId && !folderId && siteFolders.length > 0 && <div className="vault-folders">{siteFolders.map((folder) => containerCard("folders", folder))}</div>}
        {section === "sites" && <div className="vault-sites">{sites.length ? sites.map((site) => containerCard("sites", site)) : <Empty text="Create a Site for a team, project or department." />}</div>}
        {recycle && (deletedFolders.length > 0 || deletedSites.length > 0) && <div className="vault-recycled-containers">{[...deletedFolders.map((item) => ({ kind: "folders" as const, item })), ...deletedSites.map((item) => ({ kind: "sites" as const, item }))].map(({ kind, item }) => <article className="vault-container recycled" key={`${kind}-${item.id}`}><div className="vault-container-open">{kind === "folders" ? <FolderPlus /> : <Library />}<span><strong>{item.name}</strong><small>{kind === "folders" ? "Folder" : "Site"}</small></span></div><div className="vault-container-actions"><button onClick={() => void restoreContainer(kind, item)}><RotateCcw />Restore</button><button className="danger" onClick={() => void eraseContainer(kind, item)}><Trash2 />Delete forever</button></div></article>)}</div>}
        {section !== "sites" && (visibleFiles.length ? <div className="vault-grid">{visibleFiles.map((file) => <article className="vault-file" key={file.id}>
          <button className="vault-preview-tile" onClick={() => !recycle && void openPreview(file)}><FileText /><span>{file.media_type.split("/").pop()?.toUpperCase()}</span></button>
          <div className="vault-file-meta"><strong title={file.original_filename}>{file.original_filename}</strong><small>{(file.byte_size / 1048576).toFixed(2)} MB · {new Date(file.created_at).toLocaleDateString()}</small><span className="vault-access">{file.access_scope === "organization" ? <Globe2 /> : <Lock />}{file.access_scope === "organization" ? "Everyone in company" : file.access_scope === "management" ? "Admins and managers" : "Only me"}</span></div>
          <div className="vault-file-actions">{recycle ? <>{mayEdit(file) && <button onClick={() => void restore(file)}><RotateCcw />Restore</button>}{mayEdit(file) && <button className="danger" onClick={() => void erase(file)}><Trash2 />Delete forever</button>}</> : <><button onClick={() => void openPreview(file)} title="Preview"><Eye />Preview</button><button onClick={() => void download(file)} title="Download"><Download /><span>Download</span></button>{mayEdit(file) && <button onClick={() => void rename(file)} title="Rename"><Pencil /><span>Rename</span></button>}{mayEdit(file) && <button onClick={() => void toggleAccess(file)} title="Change access">{file.access_scope === "private" ? <Globe2 /> : <Lock />}<span>Access</span></button>}{mayEdit(file) && <button onClick={() => void share(file)} title="Copy secure share link"><Share2 /><span>Share</span></button>}{mayEdit(file) && <button className="danger" onClick={() => void remove(file)} title="Move to recycle bin"><Trash2 /><span>Recycle</span></button>}</>}</div>
        </article>)}</div> : (!recycle || (deletedFolders.length === 0 && deletedSites.length === 0)) && <Empty text={recycle ? "The recycle bin is empty." : "Drag and drop a file here, or use Upload file."} />)}
      </section>
      {preview && <div className="modal-backdrop preview-backdrop" onClick={() => setPreview(undefined)}><section className="file-preview" onClick={(event) => event.stopPropagation()}><header><div><strong>{preview.file.original_filename}</strong><small>Secure preview</small></div><button className="icon-button dark" onClick={() => setPreview(undefined)}><X /></button></header>{preview.file.media_type.startsWith("image/") ? <img src={preview.url} alt={preview.file.original_filename} /> : <iframe src={preview.url} title={preview.file.original_filename} />}</section></div>}
    </div>
  );
}

function AIQualityDashboard({
  metrics,
  onOpenDesign,
}: {
  metrics?: GenerationMetrics;
  onOpenDesign: (id: string) => void;
}) {
  if (!metrics) return <Empty text="AI quality metrics are loading." />;
  const maximumFailures = Math.max(
    1,
    ...metrics.failure_reasons.map((entry) => entry.count),
  );
  const maximumTrendTotal = Math.max(
    1,
    ...metrics.trends.map((entry) => entry.total),
  );
  const reasonLabel = (reason: string) =>
    reason.replace(/_/g, " ").replace(/^./, (letter) => letter.toUpperCase());
  const duration = (value?: number | null) =>
    value === null || value === undefined
      ? "—"
      : value >= 1000
        ? `${(value / 1000).toFixed(1)}s`
        : `${Math.round(value)}ms`;

  return (
    <div className="ai-quality-dashboard">
      <section className="ai-quality-hero">
        <div>
          <p className="eyebrow">MODEL OPERATIONS</p>
          <h2>Know when an image is actually good.</h2>
          <p>
            Every completed generation is measured against its editable mask and
            protected surroundings before it reaches a customer workflow.
          </p>
        </div>
        <div className={metrics.pass_rate !== null ? "quality-score" : "quality-score empty"}>
          <Gauge />
          <strong>{metrics.pass_rate === null ? "—" : `${metrics.pass_rate}%`}</strong>
          <span>evaluation pass rate</span>
        </div>
      </section>

      <section className="quality-metrics">
        <QualityMetric label="Generated" value={metrics.total_generations} detail={`${metrics.completed_generations} completed`} />
        <QualityMetric label="Evaluated" value={metrics.evaluated_generations} detail={`${metrics.unevaluated_generations} awaiting evaluation`} />
        <QualityMetric label="Passed" value={metrics.passed_generations} detail={`${metrics.failed_evaluations} need review`} positive />
        <QualityMetric label="Estimated cost" value={formatMoney(metrics.estimated_cost_usd)} detail="provider spend recorded" />
      </section>

      <section className="quality-grid">
        <article className="quality-panel">
          <div className="quality-panel-heading">
            <div><p className="eyebrow dark">QUALITY TREND</p><h3>Last 30 active days</h3></div>
            <span>{duration(metrics.average_generation_latency_ms)} avg generation</span>
          </div>
          {metrics.trends.length ? (
            <div className="quality-trend" aria-label="Daily generation quality trend">
              {metrics.trends.map((entry) => (
                <div className="trend-column" key={entry.date} title={`${entry.date}: ${entry.passed} passed, ${entry.failed} failed`}>
                  <div className="trend-bar" style={{ height: `${Math.max(12, entry.total / maximumTrendTotal * 100)}%` }}>
                    <span className="trend-pass" style={{ height: `${entry.evaluated ? entry.passed / entry.evaluated * 100 : 0}%` }} />
                  </div>
                  <small>{entry.date.slice(5)}</small>
                </div>
              ))}
            </div>
          ) : <Empty text="Generate evaluated concepts to begin the quality trend." />}
        </article>

        <article className="quality-panel">
          <div className="quality-panel-heading">
            <div><p className="eyebrow dark">FAILURE SIGNALS</p><h3>Why outputs fail</h3></div>
            <span>{duration(metrics.average_evaluation_latency_ms)} avg evaluation</span>
          </div>
          {metrics.failure_reasons.length ? (
            <div className="failure-bars">
              {metrics.failure_reasons.map((entry) => (
                <div className="failure-row" key={entry.reason}>
                  <div><span>{reasonLabel(entry.reason)}</span><strong>{entry.count}</strong></div>
                  <div className="failure-track"><span style={{ width: `${entry.count / maximumFailures * 100}%` }} /></div>
                </div>
              ))}
            </div>
          ) : <div className="quality-success"><CheckCircle2 /><span>No failed evaluations recorded.</span></div>}
        </article>
      </section>

      <section className="quality-panel">
        <div className="quality-panel-heading">
          <div><p className="eyebrow dark">MODEL COMPARISON</p><h3>Quality by deployed version</h3></div>
        </div>
        {metrics.models.length ? (
          <div className="model-table">
            <div className="model-row model-head"><span>Model</span><span>Evaluated</span><span>Pass rate</span><span>Latency</span><span>Cost</span></div>
            {metrics.models.map((model) => (
              <div className="model-row" key={model.model_version}>
                <strong title={model.model_version}>{model.model_version}</strong>
                <span>{model.evaluated}/{model.total}</span>
                <span>{model.pass_rate === null ? "—" : `${model.pass_rate}%`}</span>
                <span>{duration(model.average_latency_ms)}</span>
                <span>{formatMoney(model.estimated_cost_usd)}</span>
              </div>
            ))}
          </div>
        ) : <Empty text="No model runs have been recorded." />}
      </section>

      <section className="quality-panel">
        <div className="quality-panel-heading">
          <div><p className="eyebrow dark">HUMAN REVIEW</p><h3>Outputs needing attention</h3></div>
          <span>{metrics.review_queue.length} shown</span>
        </div>
        {metrics.review_queue.length ? (
          <div className="review-list">
            {metrics.review_queue.map((item) => (
              <button className="review-item" key={item.evaluation_id} onClick={() => onOpenDesign(item.design_project_id)}>
                <AlertTriangle />
                <span><strong>{item.prompt}</strong><small>{item.failure_reasons.map(reasonLabel).join(" · ")}</small></span>
                <span className="review-ratios"><small>Mask {(Number(item.masked_change_ratio) * 100).toFixed(1)}%</small><small>Protected {(Number(item.protected_change_ratio) * 100).toFixed(1)}%</small></span>
                <ChevronRight />
              </button>
            ))}
          </div>
        ) : <div className="quality-success"><CheckCircle2 /><span>No failed outputs are waiting for review.</span></div>}
      </section>
    </div>
  );
}

function QualityMetric({ label, value, detail, positive = false }: { label: string; value: string | number; detail: string; positive?: boolean }) {
  return <article className={positive ? "quality-metric positive" : "quality-metric"}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function Overview({
  customers,
  properties,
  designs,
  role,
  workOrders,
  preferences,
  onPreferencesChange,
  onOpenSettings,
  onNavigate,
  onOpenDesign,
}: {
  customers: Customer[];
  properties: Property[];
  designs: Design[];
  role: CurrentUser["role"];
  workOrders: WorkOrder[];
  preferences: OverviewPreferences;
  onPreferencesChange: (next: OverviewPreferences) => void;
  onOpenSettings: () => void;
  onNavigate: (view: View) => void;
  onOpenDesign: (id: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [dragging, setDragging] = useState<OverviewWidget>();
  const labels: Record<OverviewWidget, string> = {
    metrics: "Summary cards",
    guide: "Field-to-concept guide",
    recent: "Recent designs",
  };
  const visible = preferences.order.filter((widget) => preferences[widget]);

  const move = (widget: OverviewWidget, direction: -1 | 1) => {
    const order = [...preferences.order];
    const from = order.indexOf(widget);
    const to = from + direction;
    if (from < 0 || to < 0 || to >= order.length) return;
    [order[from], order[to]] = [order[to], order[from]];
    onPreferencesChange({ ...preferences, order });
  };

  const drop = (target: OverviewWidget) => {
    if (!dragging || dragging === target) return;
    const order = preferences.order.filter((widget) => widget !== dragging);
    order.splice(order.indexOf(target), 0, dragging);
    onPreferencesChange({ ...preferences, order });
    setDragging(undefined);
  };

  const renderWidget = (widget: OverviewWidget) => {
    if (widget === "metrics") {
      return (
        <section className="metrics">
          {role === "crew" ? <Metric icon={<ClipboardList />} value={workOrders.length} label="Assigned jobs" onClick={() => onNavigate("jobs")} /> : <Metric
            icon={<Users />}
            value={customers.length}
            label="Customers"
            onClick={() => onNavigate("customers")}
          />}
          <Metric
            icon={<MapPin />}
            value={properties.length}
            label="Properties"
            onClick={() => onNavigate("properties")}
          />
          <Metric
            icon={<ClipboardList />}
            value={designs.length}
            label="Designs"
            onClick={() => onNavigate("designs")}
          />
          <JobPipeline workOrders={workOrders} properties={properties} onOpen={() => onNavigate("jobs")} />
        </section>
      );
    }
    if (widget === "guide") {
      return (
        <section className="feature-card">
          <div>
            <p className="eyebrow">Field to concept</p>
            <h2>Start with the site as it is today.</h2>
            <p>
              Upload a clear, wide photo. GroundsOps removes location metadata
              and keeps the capture private to your organization.
            </p>
            <button
              className="light-button"
              onClick={() => onNavigate("designs")}
            >
              Open design studio
              <ChevronRight />
            </button>
          </div>
          <div className="terrain">
            <span className="terrain-sun" />
            <span className="terrain-line one" />
            <span className="terrain-line two" />
            <Camera />
          </div>
        </section>
      );
    }
    return (
      <section className="section-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow dark">Recent designs</p>
            <h2>Concept pipeline</h2>
          </div>
        </div>
        {designs.length ? (
          <div className="rows">
            {designs.slice(0, 4).map((design) => (
              <button
                className="data-row"
                key={design.id}
                onClick={() => onOpenDesign(design.id)}
              >
                <span className="row-icon"><Leaf /></span>
                <span>
                  <strong>{design.name}</strong>
                  <small>{design.status} · {design.goal || "No brief added"}</small>
                </span>
                <ChevronRight />
              </button>
            ))}
          </div>
        ) : (
          <Empty text="Create a design to begin collecting site photos." />
        )}
      </section>
    );
  };

  return (
    <div className="content-stack">
      <div className="overview-customize-bar">
        <p>
          {editing
            ? "Drag sections or use the arrows to arrange your workspace."
            : "Your overview, your way."}
        </p>
        <button
          className="secondary compact"
          onClick={() => setEditing((value) => !value)}
        >
          <SlidersHorizontal />
          {editing ? "Done" : "Customize overview"}
        </button>
      </div>
      {visible.map((widget, index) => (
        <div
          className={editing ? "overview-widget editing" : "overview-widget"}
          key={widget}
          draggable={editing}
          onDragStart={() => setDragging(widget)}
          onDragOver={(event) => event.preventDefault()}
          onDrop={() => drop(widget)}
        >
          {editing && (
            <div className="widget-toolbar" draggable onDragStart={() => setDragging(widget)} onDragOver={(event) => event.preventDefault()} onDrop={() => drop(widget)}>
              <span><GripVertical />{labels[widget]}</span>
              <div>
                <button disabled={index === 0} onClick={() => move(widget, -1)} aria-label={`Move ${labels[widget]} up`}><ArrowUp /></button>
                <button disabled={index === visible.length - 1} onClick={() => move(widget, 1)} aria-label={`Move ${labels[widget]} down`}><ArrowDown /></button>
                <button className="remove-widget" onClick={() => onPreferencesChange({ ...preferences, [widget]: false })} aria-label={`Remove ${labels[widget]}`}><Trash2 /></button>
              </div>
            </div>
          )}
          {renderWidget(widget)}
        </div>
      ))}
      {!visible.length && (
        <section className="section-card overview-empty">
          <Empty text="Your Overview is empty. Restore sections from Settings." />
          <button className="primary compact" onClick={onOpenSettings}>
            <Settings />
            Open settings
          </button>
        </section>
      )}
    </div>
  );
}

const pipelineStages = [
  { key: "draft", label: "Draft" },
  { key: "scheduled", label: "Scheduled" },
  { key: "in_progress", label: "In progress" },
  { key: "completed", label: "Completed" },
] as const;

function JobPipeline({ workOrders, properties, onOpen }: { workOrders: WorkOrder[]; properties: Property[]; onOpen: () => void }) {
  const total = workOrders.length;
  const counts = pipelineStages.map((stage) => ({ ...stage, value: workOrders.filter((order) => order.status === stage.key).length }));
  const now = Date.now();
  const next = workOrders
    .filter((order) => order.scheduled_start && order.status !== "completed" && new Date(order.scheduled_start).getTime() >= now)
    .sort((a, b) => new Date(a.scheduled_start!).getTime() - new Date(b.scheduled_start!).getTime())[0];
  const nextProperty = next ? properties.find((property) => property.id === next.property_id) : undefined;
  return (
    <div className="overview-chart job-pipeline">
      <header>
        <div><strong>Job pipeline</strong><small>{total === 0 ? "No work orders yet" : `${total} ${total === 1 ? "work order" : "work orders"} across all stages`}</small></div>
        <button className="text-link" type="button" onClick={onOpen}>Open job board <ChevronRight /></button>
      </header>
      <div className="pipeline-bar" role="img" aria-label={counts.map((stage) => `${stage.label}: ${stage.value}`).join(", ")}>
        {total === 0 ? <span className="pipeline-empty" /> : counts.filter((stage) => stage.value > 0).map((stage) => <span key={stage.key} className={`stage-${stage.key}`} style={{ flexGrow: stage.value }} />)}
      </div>
      <ul className="pipeline-legend">
        {counts.map((stage) => <li key={stage.key}><i className={`stage-${stage.key}`} /><span>{stage.label}</span><strong>{stage.value}</strong></li>)}
      </ul>
      {next && (
        <div className="pipeline-next">
          <CalendarClock />
          <div><small>Next scheduled</small><strong>{next.title}</strong><span>{[nextProperty?.name, formatDateTime(next.scheduled_start!)].filter(Boolean).join(" · ")}</span></div>
        </div>
      )}
    </div>
  );
}

function Metric({
  icon,
  value,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className="metric" onClick={onClick}>
      <span className="metric-icon">{icon}</span>
      <strong>{value}</strong>
      <span>{label}</span>
      <ChevronRight className="metric-arrow" />
    </button>
  );
}

function DesignStudio({
  designs,
  selected,
  selectedId,
  setSelected,
  propertyName,
  propertyLocation,
  captures,
  token,
  onAdd,
  onEdit,
  onDelete,
  onUploaded,
  onCaptureDeleted,
  setMessage,
}: {
  designs: Design[];
  selected?: Design;
  selectedId?: string;
  setSelected: (id: string) => void;
  propertyName: (id: string) => string;
  propertyLocation: string;
  captures: Capture[];
  token: string;
  onAdd: () => void;
  onEdit: (record: Design) => void;
  onDelete: (id: string) => void;
  onUploaded: () => void;
  onCaptureDeleted: () => void | Promise<void>;
  setMessage: (value: string) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [generations, setGenerations] = useState<GenerationJob[]>([]);
  const [reviews, setReviews] = useState<Record<string, GenerationReview[]>>({});
  const [prompt, setPrompt] = useState("");
  const [captureId, setCaptureId] = useState("");
  const [mask, setMask] = useState<File>();
  const [maskMeasurement, setMaskMeasurement] = useState<MaskMeasurement>();
  const [generating, setGenerating] = useState(false);
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const studioMounted = useRef(true);

  useEffect(() => {
    studioMounted.current = true;
    return () => {
      studioMounted.current = false;
    };
  }, []);

  const loadGenerations = useCallback(async (showError = false) => {
    if (!selectedId) {
      setGenerations([]);
      setReviews({});
      return;
    }
    try {
      const rows = await request<GenerationJob[]>(
        `/api/v1/design-projects/${selectedId}/generations`,
        token,
      );
      if (!studioMounted.current) return;
      setGenerations(rows);
      const completed = rows.filter((row) => row.status === "succeeded");
      const reviewRows = await Promise.all(
        completed.map(async (row) => {
          try {
            const jobReviews = await request<GenerationReview[]>(
              `/api/v1/generations/${row.id}/reviews`,
              token,
            );
            return [row.id, jobReviews] as const;
          } catch (error) {
            if (error instanceof ApiError && error.status === 404) {
              return [row.id, []] as const;
            }
            throw error;
          }
        }),
      );
      if (!studioMounted.current) return;
      setReviews(Object.fromEntries(reviewRows));
    } catch (error) {
      if (!studioMounted.current) return;
      if (error instanceof ApiError && error.status === 404) {
        setGenerations([]);
        setReviews({});
        return;
      }
      if (showError) {
        setMessage(
          error instanceof Error
            ? error.message
            : "Generations could not be loaded.",
        );
      }
    }
  }, [selectedId, setMessage, token]);

  useEffect(() => {
    void loadGenerations();
  }, [loadGenerations]);

  useEffect(() => {
    if (!generations.some((row) => row.status === "queued" || row.status === "running"))
      return;
    const timer = window.setInterval(() => void loadGenerations(), 3000);
    return () => window.clearInterval(timer);
  }, [generations, loadGenerations]);

  useEffect(() => {
    if (!captures.length) {
      setCaptureId("");
      setMask(undefined);
      setMaskMeasurement(undefined);
      return;
    }
    if (!captures.some((row) => row.id === captureId)) {
      setCaptureId(captures[0].id);
      setMask(undefined);
      setMaskMeasurement(undefined);
    }
  }, [captureId, captures]);

  async function generate(event: FormEvent) {
    event.preventDefault();
    if (!selectedId || !captureId || !mask) return;
    setGenerating(true);
    const data = new FormData();
    data.append("capture_id", captureId);
    data.append("prompt", prompt);
    data.append("mask", mask);
    if (maskMeasurement) {
      if (maskMeasurement.method)
        data.append("measurement_method", maskMeasurement.method);
      data.append("selected_pixel_count", String(maskMeasurement.selectedPixelCount));
      data.append("total_pixel_count", String(maskMeasurement.totalPixelCount));
      if (maskMeasurement.calibrationPixelLength)
        data.append("calibration_pixel_length", String(maskMeasurement.calibrationPixelLength));
      if (maskMeasurement.calibrationRealLength)
        data.append("calibration_real_length", String(maskMeasurement.calibrationRealLength));
      if (maskMeasurement.calibrationUnit)
        data.append("calibration_unit", maskMeasurement.calibrationUnit);
      if (maskMeasurement.calibrationReference)
        data.append("calibration_reference", maskMeasurement.calibrationReference);
      if (maskMeasurement.estimatedArea)
        data.append("estimated_area", String(maskMeasurement.estimatedArea));
      if (maskMeasurement.estimatedPerimeter)
        data.append("estimated_perimeter", String(maskMeasurement.estimatedPerimeter));
    }
    try {
      await request(`/api/v1/design-projects/${selectedId}/generations`, token, {
        method: "POST",
        body: data,
      });
      setPrompt("");
      setMask(undefined);
      setMaskMeasurement(undefined);
      setMessage("Generation queued. This screen will update automatically.");
      await loadGenerations();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Generation could not be started.");
    } finally {
      setGenerating(false);
    }
  }

  async function review(
    jobId: string,
    decision: GenerationReview["decision"],
  ) {
    try {
      await request(`/api/v1/generations/${jobId}/reviews`, token, {
        method: "POST",
        body: JSON.stringify({ decision, notes: reviewNotes[jobId] || null }),
      });
      setMessage(
        decision === "approved"
          ? "Generation approved."
          : decision === "rejected"
            ? "Generation rejected."
            : "Revision requested.",
      );
      await loadGenerations();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Review could not be saved.");
    }
  }
  async function upload(file?: File) {
    if (!file || !selectedId) return;
    setUploading(true);
    const data = new FormData();
    data.append("file", file);
    try {
      await request(`/api/v1/design-projects/${selectedId}/captures`, token, {
        method: "POST",
        body: data,
      });
      onUploaded();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }
  async function removeCapture(capture: Capture) {
    if (!window.confirm(`Delete ${capture.original_filename}? This cannot be undone.`)) return;
    try {
      await request(`/api/v1/captures/${capture.id}`, token, { method: "DELETE" });
      if (captureId === capture.id) {
        setCaptureId("");
        setMask(undefined);
        setMaskMeasurement(undefined);
      }
      await onCaptureDeleted();
      setMessage("Site photo deleted.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Site photo could not be deleted.");
    }
  }
  return (
    <div className="studio-grid">
      <section className="design-list section-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow dark">Projects</p>
            <h2>Designs</h2>
          </div>
          <button
            className="icon-button dark"
            onClick={onAdd}
            aria-label="New design"
          >
            <Plus />
          </button>
        </div>
        {designs.length ? (
          <div className="rows">
            {designs.map((design) => (
              <button
                key={design.id}
                className={
                  selectedId === design.id
                    ? "design-row selected"
                    : "design-row"
                }
                onClick={() => setSelected(design.id)}
              >
                <span className="row-icon">
                  <Leaf />
                </span>
                <span>
                  <strong>{design.name}</strong>
                  <small>{propertyName(design.property_id)}</small>
                </span>
                <ChevronRight />
              </button>
            ))}
          </div>
        ) : (
          <Empty text="Create a design after adding a customer and property." />
        )}
      </section>
      <section className="canvas-card">
        {selected ? (
          <>
            <div className="canvas-heading">
              <div>
                <p className="eyebrow">{propertyName(selected.property_id)}</p>
                <h2>{selected.name}</h2>
                <span className="status">{selected.status}</span>
              </div>
              <div className="design-actions">
                <button
                  className="canvas-action"
                  onClick={() => onEdit(selected)}
                >
                  <Pencil />
                  Edit
                </button>
                <button
                  className="canvas-action danger"
                  onClick={() => onDelete(selected.id)}
                >
                  <Trash2 />
                  Delete
                </button>
                <CameraMeasure
                  onMeasurement={setMaskMeasurement}
                  onError={setMessage}
                  buttonClassName="canvas-action"
                />
                <label
                  className={
                    uploading ? "upload-button disabled" : "upload-button"
                  }
                >
                  <ImagePlus />
                  {uploading ? "Sanitizing…" : "Add site photo"}
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    capture="environment"
                    disabled={uploading}
                    onChange={(event) => upload(event.target.files?.[0])}
                  />
                </label>
              </div>
            </div>
            {captures.length ? (
              <>
                <div className="capture-grid">
                  {captures.map((capture) => (
                    <article className="capture-card" key={capture.id}>
                      <CaptureImage
                        captureId={capture.id}
                        token={token}
                        alt={capture.original_filename}
                      />
                      <div>
                        <strong>{capture.original_filename}</strong>
                        <span>
                          {capture.width} × {capture.height} ·{" "}
                          {(capture.byte_size / 1024).toFixed(0)} KB
                        </span>
                      </div>
                      <button
                        type="button"
                        className="capture-delete"
                        onClick={() => void removeCapture(capture)}
                        aria-label={`Delete ${capture.original_filename}`}
                      >
                        <Trash2 />
                        Delete
                      </button>
                    </article>
                  ))}
                </div>
                <form className="generation-composer" onSubmit={generate}>
                  <div>
                    <p className="eyebrow dark">AI concept</p>
                    <h3>Generate a landscape revision</h3>
                    <p>Choose the source, describe the change and paint over every area you want AI to replace.</p>
                  </div>
                  <label>Source photo
                    <select value={captureId} onChange={(event) => setCaptureId(event.target.value)} required>
                      {captures.map((capture) => <option key={capture.id} value={capture.id}>{capture.original_filename}</option>)}
                    </select>
                  </label>
                  <label>Design prompt
                    <textarea value={prompt} minLength={2} maxLength={2000} required placeholder="Try: grass, install sod, charcoal pavers, cedar mulch or pea gravel." onChange={(event) => setPrompt(event.target.value)} />
                  </label>
                  <MaskEditor
                    captureId={captureId}
                    token={token}
                    onChange={setMask}
                    onMeasurement={setMaskMeasurement}
                    onError={setMessage}
                  />
                  <CameraMeasure onMeasurement={setMaskMeasurement} onError={setMessage} />
                  <button className="primary compact" disabled={generating || !mask || prompt.trim().length < 2}>
                    <Leaf />{generating ? "Queuing…" : "Generate concept"}
                  </button>
                </form>
                <div className="generation-history">
                  <div className="section-heading"><div><p className="eyebrow dark">Generation history</p><h3>Concept outputs</h3></div><button type="button" className="icon-button dark" onClick={() => void loadGenerations(true)} aria-label="Refresh generations"><RefreshCw /></button></div>
                  {generations.length ? generations.map((job) => {
                    const latestReview = reviews[job.id]?.[0];
                    return <article className="generation-card" key={job.id}>
                      <div className="generation-card-heading"><span className={`generation-state ${job.status}`}>{job.status}</span>{latestReview && <span className={`review-state ${latestReview.decision}`}>{latestReview.decision.replace("_", " ")}</span>}<small>{formatDateTime(job.created_at)}</small></div>
                      <p>{job.prompt}</p>
                      {job.status !== "succeeded" && job.estimated_area && job.calibration_unit && <div className="generation-measurement">
                        <strong>Measured area</strong>
                        <span>{Number(job.estimated_area).toFixed(1)} sq {job.calibration_unit}</span>
                        {job.estimated_perimeter && <span>{Number(job.estimated_perimeter).toFixed(1)} {job.calibration_unit} edge</span>}
                        <small>Photo estimate · verify on site before ordering</small>
                      </div>}
                      {job.status === "succeeded" && <MeasuredConcept job={job} token={token} />}
                      {job.status === "succeeded" && <MaterialEstimator
                        jobId={job.id}
                        token={token}
                        prompt={job.prompt}
                        propertyLocation={propertyLocation}
                        estimatedArea={job.estimated_area}
                        estimatedPerimeter={job.estimated_perimeter}
                        measurementUnit={job.calibration_unit}
                        onMessage={setMessage}
                      />}
                      {job.status === "succeeded" && latestReview?.decision === "approved" && <QuoteBuilder designId={selected.id} jobId={job.id} token={token} onMessage={setMessage} />}
                      {job.status === "failed" && <p className="generation-error">{job.error_message || "Generation failed."}</p>}
                      {job.status === "succeeded" && <div className="generation-review-controls">
                        <label>Reviewer notes<textarea value={reviewNotes[job.id] || ""} maxLength={2000} placeholder="Record what worked or what must change…" onChange={(event) => setReviewNotes((current) => ({ ...current, [job.id]: event.target.value }))} /></label>
                        <div><button type="button" className="secondary" onClick={() => void review(job.id, "revision_requested")}>Request revision</button><button type="button" className="secondary danger" onClick={() => void review(job.id, "rejected")}>Reject</button><button type="button" className="primary compact" onClick={() => void review(job.id, "approved")}><CheckCircle2 />Approve</button></div>
                      </div>}
                      {reviews[job.id]?.length ? <details className="review-audit"><summary>{reviews[job.id].length} review event{reviews[job.id].length === 1 ? "" : "s"}</summary>{reviews[job.id].map((item) => <div key={item.id}><strong>{item.decision.replace("_", " ")}</strong><span>{item.notes || "No notes"}</span><small>{formatDateTime(item.created_at)}</small></div>)}</details> : null}
                    </article>;
                  }) : <Empty text="No AI concepts have been generated for this design." />}
                </div>
              </>
            ) : (
              <label className="drop-zone">
                <Camera />
                <strong>Capture the existing site</strong>
                <span>Choose a clear JPEG, PNG or WebP image up to 10 MB.</span>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  capture="environment"
                  onChange={(event) => upload(event.target.files?.[0])}
                />
              </label>
            )}
          </>
        ) : (
          <Empty text="Select or create a design to open the capture workspace." />
        )}
      </section>
    </div>
  );
}

function EditRecordModal({
  target,
  token,
  customers,
  properties,
  close,
  complete,
}: {
  target: Exclude<EditTarget, null>;
  token: string;
  customers: Customer[];
  properties: Property[];
  close: () => void;
  complete: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const record = target.record;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const path =
      target.type === "customer"
        ? "customers"
        : target.type === "property"
          ? "properties"
          : "design-projects";
    let body: Record<string, string> = { name: String(data.get("name")) };
    if (target.type === "customer")
      body = {
        ...body,
        email: String(data.get("email")),
        phone: String(data.get("phone")),
      };
    if (target.type === "property")
      body = {
        ...body,
        customer_id: String(data.get("customer_id")),
        location: String(data.get("location")),
      };
    if (target.type === "design")
      body = {
        ...body,
        property_id: String(data.get("property_id")),
        goal: String(data.get("goal")),
      };
    try {
      await request(`/api/v1/${path}/${record.id}`, token, {
        method: "PUT",
        body: JSON.stringify(body),
      });
      complete();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Update failed.");
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop">
      <section className="modal" role="dialog" aria-modal="true">
        <div className="modal-heading">
          <div>
            <p className="eyebrow dark">Update record</p>
            <h2>Edit {target.type}</h2>
          </div>
          <button className="icon-button dark" onClick={close}>
            <X />
          </button>
        </div>
        <form onSubmit={submit}>
          <label>
            Name
            <input name="name" required defaultValue={record.name} />
          </label>
          {target.type === "customer" && (
            <>
              <label>
                Email
                <input
                  name="email"
                  type="email"
                  defaultValue={(record as Customer).email || ""}
                />
              </label>
              <label>
                Phone
                <input
                  name="phone"
                  defaultValue={(record as Customer).phone || ""}
                />
              </label>
            </>
          )}
          {target.type === "property" && (
            <>
              <label>
                Customer
                <select
                  name="customer_id"
                  defaultValue={(record as Property).customer_id || ""}
                >
                  {customers.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Location
                <input
                  name="location"
                  defaultValue={(record as Property).location || ""}
                />
              </label>
            </>
          )}
          {target.type === "design" && (
            <>
              <label>
                Property
                <select
                  name="property_id"
                  defaultValue={(record as Design).property_id}
                >
                  {properties.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Goal
                <textarea
                  name="goal"
                  rows={4}
                  defaultValue={(record as Design).goal || ""}
                />
              </label>
            </>
          )}
          {error && <p className="form-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="secondary" onClick={close}>
              Cancel
            </button>
            <button className="primary compact" disabled={busy}>
              {busy ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function Composer({
  type,
  token,
  customers,
  properties,
  close,
  complete,
}: {
  type: Exclude<Composer, null>;
  token: string;
  customers: Customer[];
  properties: Property[];
  close: () => void;
  complete: () => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const title = useMemo(
    () =>
      ({
        customer: "New customer",
        property: "New property",
        design: "New design",
      })[type],
    [type],
  );
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    let path = "";
    let body: Record<string, string> = {};
    if (type === "customer") {
      path = "/api/v1/customers";
      body = {
        name: String(data.get("name")),
        email: String(data.get("email")),
        phone: String(data.get("phone")),
      };
    } else if (type === "property") {
      path = "/api/v1/properties";
      body = {
        name: String(data.get("name")),
        location: String(data.get("location")),
        customer_id: String(data.get("customer_id")),
      };
    } else {
      path = "/api/v1/design-projects";
      body = {
        name: String(data.get("name")),
        goal: String(data.get("goal")),
        property_id: String(data.get("property_id")),
      };
    }
    try {
      await request(path, token, {
        method: "POST",
        body: JSON.stringify(body),
      });
      complete();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save.");
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="composer-title"
      >
        <div className="modal-heading">
          <div>
            <p className="eyebrow dark">GroundsOps record</p>
            <h2 id="composer-title">{title}</h2>
          </div>
          <button
            className="icon-button dark"
            onClick={close}
            aria-label="Close"
          >
            <X />
          </button>
        </div>
        <form onSubmit={submit}>
          <label>
            Name
            <input required name="name" minLength={2} />
          </label>
          {type === "customer" && (
            <>
              <label>
                Email
                <input name="email" type="email" />
              </label>
              <label>
                Phone
                <input name="phone" />
              </label>
            </>
          )}
          {type === "property" && (
            <>
              <label>
                Customer
                <select required name="customer_id" defaultValue="">
                  <option value="" disabled>
                    Select a customer
                  </option>
                  {customers.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Location
                <input name="location" placeholder="Burnaby, BC" />
              </label>
            </>
          )}
          {type === "design" && (
            <>
              <label>
                Property
                <select required name="property_id" defaultValue="">
                  <option value="" disabled>
                    Select a property
                  </option>
                  {properties.map((property) => (
                    <option key={property.id} value={property.id}>
                      {property.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Goal
                <textarea
                  name="goal"
                  rows={4}
                  placeholder="Replace the worn lawn with a paver seating area."
                />
              </label>
            </>
          )}
          {error && <p className="form-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="secondary" onClick={close}>
              Cancel
            </button>
            <button className="primary compact" disabled={busy}>
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}


