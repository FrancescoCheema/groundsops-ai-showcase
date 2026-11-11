"use client";

import { useEffect, useState } from "react";
import { ChevronRight, Clock3, MapPin, Plus, Route, X } from "lucide-react";
import { Empty } from "@/features/shared/empty";
import { OrganizationUser, Property, Timesheet, WorkOrder, request } from "@/lib/api";
import { JobCompletion } from "@/features/scheduling/job-completion";
import { formatDateTime, formatMoney, plural } from "@/features/shared/format";

export function JobMap({ properties, workOrders, users, token, refresh, canManage }: { properties: Property[]; workOrders: WorkOrder[]; users: OrganizationUser[]; token: string; refresh: () => Promise<void>; canManage: boolean }) {
  const located = properties.filter((property) => property.location?.trim());
  const [selectedId, setSelectedId] = useState(located[0]?.id || "");
  const selected = located.find((property) => property.id === selectedId) || located[0];
  const address = selected?.location || "";
  const encoded = encodeURIComponent(address);
  const [origin, setOrigin] = useState("");
  const [showRoute, setShowRoute] = useState(false);
  const [travelMode, setTravelMode] = useState<"driving" | "walking" | "transit" | "bicycling">("driving");
  const [locationMessage, setLocationMessage] = useState("");
  const [externalMap, setExternalMap] = useState<"apple" | "google">("google");
  const [recentRoutes, setRecentRoutes] = useState<string[]>([]);
  const [jobTitle, setJobTitle] = useState("");
  const [jobProperty, setJobProperty] = useState(properties[0]?.id || "");
  const [jobUser, setJobUser] = useState("");
  const [jobStart, setJobStart] = useState("");
  const [jobEnd, setJobEnd] = useState("");
  const [jobPriority, setJobPriority] = useState<WorkOrder["priority"]>("normal");
  const [dispatchError, setDispatchError] = useState("");
  const [completingJob, setCompletingJob] = useState<WorkOrder>();
  const directionFlags = { driving: "d", walking: "w", transit: "r", bicycling: "b" };
  const routeSource = showRoute && origin
    ? `https://www.google.com/maps?saddr=${encodeURIComponent(origin)}&daddr=${encoded}&dirflg=${directionFlags[travelMode]}&output=embed`
    : `https://www.google.com/maps?q=${encoded}&output=embed`;
  const selectedJobs = workOrders.filter((job) => job.property_id === selected?.id);
  const busyJobs = selectedJobs.filter((job) => job.status === "approved").length;
  useEffect(() => {
    const appleDevice = /iPad|iPhone|iPod|Macintosh/.test(navigator.userAgent);
    setExternalMap(appleDevice ? "apple" : "google");
    setRecentRoutes(JSON.parse(localStorage.getItem("groundsops-recent-routes") || "[]"));
  }, []);
  function planRoute() {
    setShowRoute(true);
    const route = `${origin}|||${address}|||${travelMode}`;
    const next = [route, ...recentRoutes.filter((item) => item !== route)].slice(0, 6);
    setRecentRoutes(next);
    localStorage.setItem("groundsops-recent-routes", JSON.stringify(next));
  }
  function useMyLocation() {
    setLocationMessage("");
    if (!window.isSecureContext) {
      setLocationMessage("Current location needs HTTPS on this device. Enter your starting address instead.");
      return;
    }
    if (!navigator.geolocation) {
      setLocationMessage("Location services are not supported by this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setOrigin(`${coords.latitude},${coords.longitude}`);
        setLocationMessage("Current location added.");
      },
      (error) => setLocationMessage(
        error.code === error.PERMISSION_DENIED
          ? "Location permission was denied. Allow it in browser settings or enter an address."
          : "Your location could not be determined. Enter a starting address instead.",
      ),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }
  const externalRoute = externalMap === "apple"
    ? `https://maps.apple.com/?saddr=${encodeURIComponent(origin)}&daddr=${encoded}&dirflg=${directionFlags[travelMode]}`
    : `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origin)}&destination=${encoded}&travelmode=${travelMode}`;
  async function createScheduledJob() {
    setDispatchError("");
    try {
      await request("/api/v1/work-orders", token, { method: "POST", body: JSON.stringify({ property_id: jobProperty, title: jobTitle, description: "Scheduled through dispatch board", assigned_user_id: jobUser || null, scheduled_start: jobStart ? new Date(jobStart).toISOString() : null, scheduled_end: jobEnd ? new Date(jobEnd).toISOString() : null, priority: jobPriority }) });
      setJobTitle("");
      await refresh();
    } catch (caught) { setDispatchError(caught instanceof Error ? caught.message : "Job could not be scheduled."); }
  }
  async function moveJob(job: WorkOrder, status: string) {
    if (status === "completed") {
      setCompletingJob(job);
      return;
    }
    await request(`/api/v1/work-orders/${job.id}`, token, { method: "PUT", body: JSON.stringify({ property_id: job.property_id, title: job.title, description: job.description, assigned_user_id: job.assigned_user_id || null, scheduled_start: job.scheduled_start || null, scheduled_end: job.scheduled_end || null, priority: job.priority || "normal", status }) });
    await refresh();
  }
  return (
    <div className="content-stack">
      <section className="job-map-layout">
        <div className="section-card job-list">
          <div className="section-heading"><div><p className="eyebrow dark">Field locations</p><h2>Jobs and addresses</h2></div><span className="status-light">{located.length} mapped</span></div>
          {located.length ? located.map((property) => (
            <button key={property.id} className={selected?.id === property.id ? "job-address active" : "job-address"} onClick={() => setSelectedId(property.id)}>
              <MapPin /><span><strong>{property.name}</strong><small>{property.location}</small><small>{plural(workOrders.filter((job) => job.property_id === property.id).length, "job")}</small></span><ChevronRight />
            </button>
          )) : <Empty text="Add an address to a property to place it on the job map." />}
        </div>
        <section className="job-map-card">
          {selected ? <>
            <iframe title={`Map and route to ${selected.name}`} src={routeSource} loading="lazy" referrerPolicy="no-referrer-when-downgrade" />
            <div className="route-planner"><div className="route-summary"><span className={busyJobs ? "route-load busy" : "route-load available"}>{busyJobs ? `${busyJobs} active job${busyJobs === 1 ? "" : "s"}` : "Route available"}</span><strong>{selected.name}</strong><small>{address}</small></div><div className="travel-modes">{(["driving", "walking", "transit", "bicycling"] as const).map((mode) => <button className={travelMode === mode ? "active" : ""} key={mode} onClick={() => { setTravelMode(mode); setShowRoute(Boolean(origin)); }}>{mode[0].toUpperCase() + mode.slice(1)}</button>)}</div><div className="route-input"><input list="job-address-suggestions" value={origin} onChange={(event) => { setOrigin(event.target.value); setShowRoute(false); }} placeholder="Starting address or use your location"/><datalist id="job-address-suggestions">{located.map((property) => <option key={property.id} value={property.location || ""}>{property.name}</option>)}</datalist><button className="secondary compact" onClick={useMyLocation}><MapPin />My location</button><button className="primary compact" disabled={!origin} onClick={planRoute}><Route />Show route</button></div>{locationMessage && <p className="location-message">{locationMessage}</p>}{showRoute && <div className="chosen-route"><strong>Chosen route</strong><span>{origin} → {address}</span><small>{travelMode}. Directions are displayed in the map above.</small></div>}<a className="google-route" href={externalRoute} target="_blank" rel="noreferrer">Continue in {externalMap === "apple" ? "Apple Maps" : "Google Maps"} <ChevronRight /></a></div>
          </> : <Empty text="No job address selected." />}
        </section>
      </section>
      {recentRoutes.length > 0 && <section className="section-card recent-routes"><div className="section-heading"><div><p className="eyebrow dark">History</p><h2>Recent routes</h2></div><button className="secondary compact" onClick={() => { setRecentRoutes([]); localStorage.removeItem("groundsops-recent-routes"); }}>Clear all</button></div>{recentRoutes.map((route) => { const [from, to, mode] = route.split("|||"); return <div className="recent-route" key={route}><button onClick={() => { setOrigin(from); setTravelMode(mode as typeof travelMode); setShowRoute(true); }}><Route /><span><strong>{to}</strong><small>From {from} · {mode}</small></span></button><button className="mini-icon-button" onClick={() => { const next = recentRoutes.filter((item) => item !== route); setRecentRoutes(next); localStorage.setItem("groundsops-recent-routes", JSON.stringify(next)); }}><X /></button></div>; })}</section>}
      {canManage && <section className="section-card dispatch-create"><div className="section-heading"><div><p className="eyebrow dark">Scheduling</p><h2>Schedule a job</h2></div></div><div className="dispatch-form"><label>Job title<input value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} /></label><label>Property<select value={jobProperty} onChange={(event) => setJobProperty(event.target.value)}>{properties.map((property) => <option key={property.id} value={property.id}>{property.name}</option>)}</select></label><label>Assign crew<select value={jobUser} onChange={(event) => setJobUser(event.target.value)}><option value="">Unassigned</option>{users.map((user) => <option key={user.id} value={user.id}>{user.display_name} · {user.role}</option>)}</select></label><label>Start<input type="datetime-local" value={jobStart} onChange={(event) => setJobStart(event.target.value)} /></label><label>End<input type="datetime-local" value={jobEnd} onChange={(event) => setJobEnd(event.target.value)} /></label><label>Priority<select value={jobPriority} onChange={(event) => setJobPriority(event.target.value as WorkOrder["priority"])}><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option></select></label><button className="primary" disabled={!jobTitle.trim() || !jobProperty} onClick={() => void createScheduledJob()}><Plus />Schedule job</button></div>{dispatchError && <p className="form-error">{dispatchError}</p>}</section>}
      <section className="section-card"><div className="section-heading"><div><p className="eyebrow dark">Dispatch</p><h2>Job board</h2></div><span className="status-light">Drag jobs between stages</span></div><div className="dispatch-board">{(["draft", "scheduled", "in_progress", "completed"] as const).map((status) => <div className="dispatch-column" key={status} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { const job = workOrders.find((row) => row.id === event.dataTransfer.getData("text/job-id")); if (job && canManage) void moveJob(job, status); }}><h3>{status.replace("_", " ")}<span>{workOrders.filter((job) => job.status === status).length}</span></h3>{workOrders.filter((job) => job.status === status).map((job) => <article key={job.id} draggable={canManage} onDragStart={(event) => event.dataTransfer.setData("text/job-id", job.id)}><span className={`priority ${job.priority}`}>{job.priority}</span><strong>{job.title}</strong><small>{properties.find((property) => property.id === job.property_id)?.name || "Property"}</small><small>{job.scheduled_start ? formatDateTime(job.scheduled_start) : "Not scheduled"}</small><small>{users.find((user) => user.id === job.assigned_user_id)?.display_name || "Unassigned"}</small>{job.actual_total && <small>Actual {formatMoney(job.actual_total)}</small>}</article>)}</div>)}</div></section>
      {completingJob && <JobCompletion job={completingJob} token={token} close={() => setCompletingJob(undefined)} completed={refresh} />}
    </div>
  );
}

export function TimesheetsView({
  token,
  properties,
  entries,
  refresh,
  setMessage,
  locale,
  timezone,
  notifications,
  userId,
  canManage,
}: {
  token: string;
  properties: Property[];
  entries: Timesheet[];
  refresh: () => Promise<void>;
  setMessage: (value: string) => void;
  locale: string;
  timezone: string;
  notifications: boolean;
  userId: string;
  canManage: boolean;
}) {
  const [propertyId, setPropertyId] = useState("");
  const [busy, setBusy] = useState(false);
  const [range, setRange] = useState("7");
  const [customTime, setCustomTime] = useState(false);
  const [clockTime, setClockTime] = useState("");
  const running = entries.find(
    (entry) => entry.user_id === userId && entry.status === "running",
  );
  const duration = (entry: Timesheet) => {
    const end = entry.ended_at ? new Date(entry.ended_at) : new Date();
    const minutes = Math.max(
      0,
      Math.floor(
        (end.getTime() - new Date(entry.started_at).getTime()) / 60000,
      ),
    );
    return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
  };
  const filteredEntries = entries.filter((entry) =>
    range === "all"
      ? true
      : new Date(entry.started_at).getTime() >= Date.now() - Number(range) * 86400000,
  );
  async function toggleClock() {
    setBusy(true);
    setMessage("");
    try {
      if (running)
        await request(`/api/v1/timesheets/${running.id}/clock-out`, token, {
          method: "POST",
          body: JSON.stringify({
            ended_at: customTime && clockTime ? new Date(clockTime).toISOString() : null,
          }),
        });
      else
        await request("/api/v1/timesheets/clock-in", token, {
          method: "POST",
          body: JSON.stringify({
            property_id: propertyId || null,
            started_at: customTime && clockTime ? new Date(clockTime).toISOString() : null,
          }),
        });
      await refresh();
      setCustomTime(false);
      setClockTime("");
      if (notifications && "Notification" in window && Notification.permission === "granted") {
        new Notification(running ? "Timesheet submitted" : "Timesheet started", {
          body: running ? "Your completed shift is ready for review." : "GroundsOps is now tracking this shift.",
        });
      }
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Timesheet could not be updated.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function approve(entry: Timesheet) {
    await request(`/api/v1/timesheets/${entry.id}/approve`, token, { method: "POST" });
    await refresh();
  }
  return (
    <div className="content-stack">
      <section className="clock-card">
        <div>
          <p className="eyebrow">Crew time</p>
          <h2>{running ? "Shift in progress" : "Ready for the next shift"}</h2>
          <p>
            {running
              ? `Started ${new Date(running.started_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · ${running.property_name || "No property"}`
              : "Clock time against a property for an accurate job record."}
          </p>
          {!running && (
            <select
              className="clock-property"
              value={propertyId}
              onChange={(event) => setPropertyId(event.target.value)}
            >
              <option value="">No property</option>
              {properties.map((property) => (
                <option key={property.id} value={property.id}>
                  {property.name}
                </option>
              ))}
            </select>
          )}
          <div className="time-entry-options">
            <label className="time-mode">
              <input
                type="checkbox"
                checked={customTime}
                onChange={(event) => {
                  setCustomTime(event.target.checked);
                  if (event.target.checked && !clockTime) {
                    const now = new Date(Date.now() - new Date().getTimezoneOffset() * 60000);
                    setClockTime(now.toISOString().slice(0, 16));
                  }
                }}
              />
              {running ? "Use a specific clock-out time" : "Use a specific clock-in time"}
            </label>
            {customTime && <label className="custom-clock-time">Date and time<input type="datetime-local" value={clockTime} max={new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16)} onChange={(event) => setClockTime(event.target.value)} /></label>}
          </div>
        </div>
        <button
          disabled={busy}
          className={running ? "clock-button stop" : "clock-button"}
          onClick={toggleClock}
        >
          <Clock3 />
          {busy ? "Saving…" : running ? "Clock out" : "Clock in"}
        </button>
      </section>
      <section className="section-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow dark">Persistent records</p>
            <h2>Employee timesheets</h2>
          </div>
          <select className="range-select" value={range} onChange={(event) => setRange(event.target.value)} aria-label="Timesheet time range">
            <option value="7">Last 7 days</option><option value="30">Last month</option><option value="365">Last year</option><option value="all">All time</option>
          </select>
        </div>
        {filteredEntries.length ? (
          <div className="timesheet-table">
            <div className="table-head">
              <span>Employee</span>
              <span>Property</span>
              <span>Time</span>
            </div>
            {filteredEntries.map((entry) => (
              <div className="table-row" key={entry.id}>
                <strong>{entry.employee_name}<small>{new Intl.DateTimeFormat(locale, { timeZone: timezone, month: "short", day: "numeric", year: "numeric" }).format(new Date(entry.started_at))}</small></strong>
                <span>{entry.property_name || "Unassigned"}</span>
                <span>
                  {entry.status === "running" ? "Running" : duration(entry)}
                  {canManage && entry.status === "submitted" && <button className="approve-time" onClick={() => void approve(entry)}>Approve</button>}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <Empty text="No timesheets were found in this time range." />
        )}
      </section>
    </div>
  );
}
