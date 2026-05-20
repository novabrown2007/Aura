const state = {
  page: "chatPage",
  calendarView: "day",
  calendarDate: new Date().toISOString().slice(0, 10),
  selectedCalendarId: "",
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const payload = await response.json();
  if (!payload.ok) throw new Error(payload.error || "Request failed.");
  return payload.data;
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("visible");
  clearTimeout(toast.timeout);
  toast.timeout = setTimeout(() => element.classList.remove("visible"), 3200);
}

function formData(form) {
  const data = {};
  new FormData(form).forEach((value, key) => {
    if (value !== "") data[key] = value;
  });
  $$("input[type='checkbox']", form).forEach((input) => {
    data[input.name] = input.checked;
  });
  ["attendees", "categories"].forEach((key) => {
    if (data[key]) data[key] = data[key].split(",").map((item) => item.trim()).filter(Boolean);
  });
  if (!data.calendar_id && state.selectedCalendarId) data.calendar_id = state.selectedCalendarId;
  return data;
}

function showPage(pageId) {
  state.page = pageId;
  $$(".page").forEach((page) => page.classList.toggle("active", page.id === pageId));
  $$(".side-button").forEach((button) => button.classList.toggle("active", button.dataset.page === pageId));
  if (pageId === "remindersPage") loadReminders();
  if (pageId === "calendarPage") {
    loadCalendars();
    loadCalendarView();
  }
}

function renderRows(container, rows, emptyText, actions = {}) {
  container.innerHTML = "";
  if (!rows || rows.length === 0) {
    container.innerHTML = `<div class="item-card muted">${emptyText}</div>`;
    return;
  }
  rows.forEach((row) => {
    const card = document.createElement("article");
    card.className = "item-card";
    const title = row.title || row.name || "Untitled";
    const when = row.start_at || row.due_at || row.remind_at || row.reminder_at || row.notification_at || row.created_at || "";
    const detail = row.description || row.content || row.message || row.status || "";
    card.innerHTML = `
      <h3>${escapeHtml(title)}</h3>
      <div class="muted">${escapeHtml(when || "")}</div>
      <p>${escapeHtml(detail || "")}</p>
    `;
    if (actions.delete && row.id !== undefined) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Delete";
      button.addEventListener("click", () => actions.delete(row.id));
      card.append(button);
    }
    container.append(card);
  });
}

async function sendChat(event) {
  event.preventDefault();
  const input = $("#chatInput");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  appendMessage("You", message, "you");
  try {
    const result = await api("/api/chat", { method: "POST", body: { message } });
    appendMessage("Aura", result.response, "aura");
  } catch (error) {
    appendMessage("Aura", `Error: ${error.message}`, "aura");
  }
}

function appendMessage(speaker, message, className) {
  const row = document.createElement("div");
  row.className = `message ${className}`;
  row.innerHTML = `<strong>${escapeHtml(speaker)}</strong><span>${escapeHtml(message)}</span>`;
  $("#transcript").append(row);
  row.scrollIntoView({ block: "end" });
}

async function loadReminders() {
  try {
    const rows = await api("/api/reminders");
    renderRows($("#remindersList"), rows, "No reminders scheduled yet.", {
      delete: async (id) => {
        await api(`/api/reminders/${id}`, { method: "DELETE" });
        toast("Reminder deleted.");
        loadReminders();
      },
    });
  } catch (error) {
    toast(error.message);
  }
}

async function createReminder(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api("/api/reminders", { method: "POST", body: formData(form) });
    form.reset();
    $("#reminderDialog").close();
    toast("Reminder created.");
    loadReminders();
  } catch (error) {
    toast(error.message);
  }
}

async function loadNotifications() {
  try {
    const rows = await api("/api/notifications");
    renderRows($("#notificationsList"), rows, "No notifications.", {
      delete: async (id) => {
        await api(`/api/notifications/${id}`, { method: "DELETE" });
        toast("Notification deleted.");
        loadNotifications();
      },
    });
  } catch (error) {
    toast(error.message);
  }
}

async function loadCalendars() {
  try {
    const result = await api("/api/calendar/calendars");
    const select = $("#calendarSelect");
    state.selectedCalendarId = result.selected_calendar_id || "";
    select.innerHTML = `<option value="">Default calendar</option>`;
    (result.calendars || []).forEach((calendar) => {
      const option = document.createElement("option");
      option.value = calendar.id;
      option.textContent = calendar.name;
      option.selected = String(calendar.id) === String(state.selectedCalendarId);
      select.append(option);
    });
  } catch (error) {
    toast(error.message);
  }
}

async function selectCalendar() {
  state.selectedCalendarId = $("#calendarSelect").value;
  await api("/api/calendar/select", { method: "POST", body: { calendar_id: state.selectedCalendarId || null } });
  loadCalendarView();
}

async function loadCalendarView() {
  $("#calendarDate").value = state.calendarDate;
  $$("#calendarTabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === state.calendarView);
  });
  const params = new URLSearchParams({
    view: state.calendarView,
    date: state.calendarDate,
  });
  if (state.selectedCalendarId) params.set("calendar_id", state.selectedCalendarId);
  try {
    const data = await api(`/api/calendar/view?${params}`);
    renderCalendar(data);
  } catch (error) {
    toast(error.message);
  }
}

function renderCalendar(data) {
  const grid = $("#calendarGrid");
  grid.className = `calendar-grid ${state.calendarView}`;
  grid.innerHTML = "";
  $("#calendarSummary").textContent = calendarSummary(data);

  if (state.calendarView === "year") {
    (data.months || []).forEach((month) => {
      const rows = allCalendarRows(month);
      grid.append(bucket(month.month || "Month", rows.slice(0, 4), `${rows.length} item(s)`));
    });
    return;
  }

  if (state.calendarView === "month") {
    const rowsByDay = groupByDate(allCalendarRows(data));
    Object.keys(rowsByDay).sort().forEach((day) => grid.append(bucket(day, rowsByDay[day])));
    if (!grid.children.length) grid.append(bucket("Month", [], "No calendar items."));
    return;
  }

  if (state.calendarView === "week") {
    const rowsByDay = groupByDate(allCalendarRows(data));
    const start = new Date(`${data.week_start}T00:00:00`);
    for (let offset = 0; offset < 7; offset += 1) {
      const day = new Date(start);
      day.setDate(start.getDate() + offset);
      const key = day.toISOString().slice(0, 10);
      grid.append(bucket(key, rowsByDay[key] || []));
    }
    return;
  }

  const sections = [
    ["Events", data.events || []],
    ["Tasks", data.tasks || []],
    ["Reminders", data.reminders || []],
  ];
  sections.forEach(([title, rows]) => grid.append(bucket(title, rows)));
}

function calendarSummary(data) {
  if (state.calendarView === "year") return `Year ${data.year}`;
  if (state.calendarView === "month") return `Month ${data.month}`;
  if (state.calendarView === "week") return `Week ${data.week_start} to ${data.week_end}`;
  return `Day ${data.day}`;
}

function bucket(title, rows, emptyText = "No items.") {
  const element = document.createElement("section");
  element.className = "calendar-bucket";
  element.innerHTML = `<h3>${escapeHtml(title)}</h3>`;
  if (!rows || rows.length === 0) {
    element.insertAdjacentHTML("beforeend", `<div class="muted">${escapeHtml(emptyText)}</div>`);
    return element;
  }
  rows.forEach((row) => {
    const titleText = row.title || row.name || "Untitled";
    const when = row.start_at || row.due_at || row.remind_at || "";
    element.insertAdjacentHTML("beforeend", `<div class="pill"><strong>${escapeHtml(titleText)}</strong><br><span class="muted">${escapeHtml(when)}</span></div>`);
  });
  return element;
}

function allCalendarRows(data) {
  return [
    ...(data.events || []).map((row) => ({ ...row, kind: "event" })),
    ...(data.tasks || []).map((row) => ({ ...row, kind: "task" })),
    ...(data.reminders || []).map((row) => ({ ...row, kind: "reminder" })),
  ];
}

function groupByDate(rows) {
  return rows.reduce((grouped, row) => {
    const raw = row.start_at || row.due_at || row.remind_at || state.calendarDate;
    const key = String(raw).slice(0, 10);
    grouped[key] = grouped[key] || [];
    grouped[key].push(row);
    return grouped;
  }, {});
}

function shiftCalendar(offset) {
  const current = new Date(`${state.calendarDate}T00:00:00`);
  if (state.calendarView === "month") current.setMonth(current.getMonth() + offset);
  else if (state.calendarView === "year") current.setFullYear(current.getFullYear() + offset);
  else current.setDate(current.getDate() + offset * (state.calendarView === "week" ? 7 : 1));
  state.calendarDate = current.toISOString().slice(0, 10);
  loadCalendarView();
}

async function createEvent(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api("/api/calendar/events", { method: "POST", body: formData(form) });
    form.reset();
    $("#eventDialog").close();
    toast("Event created.");
    loadCalendarView();
  } catch (error) {
    toast(error.message);
  }
}

async function handleToolAction(action, form) {
  const data = formData(form);
  try {
    if (action === "create-event") await api("/api/calendar/events", { method: "POST", body: data });
    if (action === "update-event") await api(`/api/calendar/events/${requireId(data)}`, { method: "PUT", body: data });
    if (action === "delete-event") await api(`/api/calendar/events/${requireId(data)}`, { method: "DELETE" });
    if (action === "create-task") await api("/api/calendar/tasks", { method: "POST", body: data });
    if (action === "update-task") await api(`/api/calendar/tasks/${requireId(data)}`, { method: "PUT", body: data });
    if (action === "delete-task") await api(`/api/calendar/tasks/${requireId(data)}`, { method: "DELETE" });
    if (action === "create-calendar-reminder") await api("/api/calendar/reminders", { method: "POST", body: data });
    if (action === "update-calendar-reminder") await api(`/api/calendar/reminders/${requireId(data)}`, { method: "PUT", body: data });
    if (action === "delete-calendar-reminder") await api(`/api/calendar/reminders/${requireId(data)}`, { method: "DELETE" });
    if (action === "create-calendar") {
      await api("/api/calendar/calendars", { method: "POST", body: data });
      await loadCalendars();
    }
    if (action === "search-calendar") {
      const result = await api("/api/calendar/search", { method: "POST", body: data });
      renderRows($("#searchResults"), allCalendarRows(result), "No matching calendar items.");
      return;
    }
    toast("Calendar updated.");
    loadCalendarView();
  } catch (error) {
    toast(error.message);
  }
}

async function handleAdvanced(action, form) {
  const data = formData(form);
  const fields = {};
  if (data.title) fields.title = data.title;
  if (data.kind === "task") {
    if (data.start_at) fields.due_at = data.start_at;
    if (data.end_at) fields.due_at = data.end_at;
  } else if (data.kind === "reminder") {
    if (data.start_at) fields.remind_at = data.start_at;
    if (data.end_at) fields.remind_at = data.end_at;
  } else {
    if (data.start_at) fields.start_at = data.start_at;
    if (data.end_at) fields.end_at = data.end_at;
  }
  try {
    let result;
    if (action === "check-conflicts") {
      result = await api("/api/calendar/conflicts", {
        method: "POST",
        body: { start_at: data.start_at, end_at: data.end_at, calendar_id: state.selectedCalendarId || null },
      });
    } else {
      const body = { ...data, fields };
      delete body.title;
      delete body.start_at;
      delete body.end_at;
      const path = {
        "update-occurrence": "/api/calendar/occurrences/update",
        "cancel-occurrence": "/api/calendar/occurrences/cancel",
        "update-series": "/api/calendar/series/update",
        "delete-series": "/api/calendar/series/delete",
      }[action];
      result = await api(path, { method: "POST", body });
    }
    renderRows($("#advancedResults"), Array.isArray(result) ? result : [result], "No results.");
    loadCalendarView();
  } catch (error) {
    toast(error.message);
  }
}

function requireId(data) {
  if (!data.id) throw new Error("ID is required.");
  return data.id;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

function bindEvents() {
  $("#sidebarToggle").addEventListener("click", () => $("#sidebar").classList.toggle("collapsed"));
  $$(".side-button").forEach((button) => button.addEventListener("click", () => showPage(button.dataset.page)));
  $("#chatForm").addEventListener("submit", sendChat);
  $("#newReminderButton").addEventListener("click", () => $("#reminderDialog").showModal());
  $("#newEventButton").addEventListener("click", () => $("#eventDialog").showModal());
  $("#reminderForm").addEventListener("submit", createReminder);
  $("#eventForm").addEventListener("submit", createEvent);
  $$("[data-close-dialog]").forEach((button) => button.addEventListener("click", () => button.closest("dialog").close()));
  $("#notificationsButton").addEventListener("click", () => {
    $("#notificationsDrawer").classList.remove("hidden");
    loadNotifications();
  });
  $("#closeNotifications").addEventListener("click", () => $("#notificationsDrawer").classList.add("hidden"));
  $("#profileButton").addEventListener("click", () => toast("Profile controls are not wired to a backend module yet."));
  $("#calendarDate").addEventListener("change", (event) => {
    state.calendarDate = event.target.value || state.calendarDate;
    loadCalendarView();
  });
  $("#calendarSelect").addEventListener("change", selectCalendar);
  $("#prevRange").addEventListener("click", () => shiftCalendar(-1));
  $("#nextRange").addEventListener("click", () => shiftCalendar(1));
  $("#todayRange").addEventListener("click", () => {
    state.calendarDate = new Date().toISOString().slice(0, 10);
    loadCalendarView();
  });
  $$("#calendarTabs button").forEach((button) => button.addEventListener("click", () => {
    state.calendarView = button.dataset.view;
    loadCalendarView();
  }));
  $$("#toolTabs button").forEach((button) => button.addEventListener("click", () => {
    $$("#toolTabs button").forEach((item) => item.classList.toggle("active", item === button));
    $$(".tool-form").forEach((panel) => panel.classList.toggle("active", panel.dataset.toolPanel === button.dataset.tool));
  }));
  $$("#toolTabs button")[0].classList.add("active");
  $$(".tool-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      handleToolAction(event.submitter.dataset.action, form);
    });
    $$("button[data-action]", form).forEach((button) => {
      if (button.type !== "submit") {
        button.addEventListener("click", () => {
          if (form.id === "advancedTool") handleAdvanced(button.dataset.action, form);
          else handleToolAction(button.dataset.action, form);
        });
      }
    });
  });
}

bindEvents();
$("#calendarDate").value = state.calendarDate;
