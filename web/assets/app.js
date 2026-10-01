const WIDGET_SRC = "https://telegram.org/js/telegram-widget.js?22";
const DONE = 2;
const MISSED = 1;
const MOBILE_WEEKS = 5;
let copy;

const $ = (id) => document.getElementById(id);

async function api(path, options) {
  const response = await fetch(path, { credentials: "same-origin", ...options });
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

function addDays(isoDate, count) {
  const date = new Date(`${isoDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + count);
  return date;
}

function formatDate(date) {
  return `${date.getUTCDate()} ${copy.months[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

function overallLevel(ratio) {
  if (ratio === null) return "none";
  if (ratio === 0) return "0";
  return String(Math.min(4, Math.ceil(ratio * 4)));
}

function habitLevel(state) {
  if (state === DONE) return "4";
  return state === MISSED ? "0" : "none";
}

function renderGrid(start, values, levelOf, describe) {
  const grid = document.createElement("div");
  grid.className = "grid";
  values.forEach((value, index) => {
    const cell = document.createElement("div");
    cell.className = "cell";
    cell.dataset.level = levelOf(value);
    cell.title = `${formatDate(addDays(start, index))}: ${describe(value)}`;
    grid.append(cell);
  });
  const scroll = document.createElement("div");
  scroll.className = "grid-scroll";
  scroll.append(grid);
  return scroll;
}

function renderMobileCalendar(start, values, levelOf, describe) {
  const calendar = document.createElement("div");
  calendar.className = "mobile-calendar";

  const latestIndex = values.length - 1;
  const firstIndex = Math.max(0, Math.floor(latestIndex / 7) * 7 - (MOBILE_WEEKS - 1) * 7);
  const range = document.createElement("p");
  range.className = "calendar-range";
  range.textContent = `${formatDate(addDays(start, firstIndex))} — ${formatDate(addDays(start, latestIndex))}`;

  const grid = document.createElement("div");
  grid.className = "calendar-grid";
  for (const weekday of copy.weekdays) {
    const label = document.createElement("span");
    label.className = "weekday";
    label.textContent = weekday;
    grid.append(label);
  }

  const detail = document.createElement("p");
  detail.className = "calendar-detail";
  detail.setAttribute("aria-live", "polite");
  for (let index = firstIndex; index < firstIndex + MOBILE_WEEKS * 7; index++) {
    if (index > latestIndex) {
      const empty = document.createElement("span");
      empty.className = "future-day";
      grid.append(empty);
      continue;
    }

    const date = addDays(start, index);
    const value = values[index];
    const description = `${formatDate(date)}: ${describe(value)}`;
    const day = document.createElement("button");
    day.type = "button";
    day.className = "calendar-day cell";
    day.dataset.level = levelOf(value);
    day.textContent = String(date.getUTCDate());
    day.setAttribute("aria-label", description);
    day.setAttribute("aria-pressed", "false");
    day.addEventListener("click", () => {
      detail.textContent = description;
      grid.querySelector(".calendar-day[aria-pressed='true']")?.setAttribute("aria-pressed", "false");
      day.setAttribute("aria-pressed", "true");
    });
    if (index === latestIndex) {
      day.classList.add("today");
      day.setAttribute("aria-pressed", "true");
      detail.textContent = description;
    }
    grid.append(day);
  }

  calendar.append(range, grid, detail);
  return calendar;
}

function renderHistory(start, values, levelOf, describe) {
  const history = document.createElement("details");
  history.className = "history";
  const summary = document.createElement("summary");
  summary.textContent = copy.year;
  history.append(summary);
  history.addEventListener("toggle", () => {
    if (history.open) {
      if (!history.querySelector(".grid-scroll")) {
        history.append(renderGrid(start, values, levelOf, describe));
      }
      const scroll = history.querySelector(".grid-scroll");
      scroll.scrollLeft = scroll.scrollWidth;
    }
  });
  return history;
}

function renderVisualizations(start, values, levelOf, describe) {
  const desktop = renderGrid(start, values, levelOf, describe);
  desktop.classList.add("desktop-grid");
  return [
    desktop,
    renderMobileCalendar(start, values, levelOf, describe),
    renderHistory(start, values, levelOf, describe),
  ];
}

function describeOverall(ratio) {
  return ratio === null ? copy.no_habits : `${Math.round(ratio * 100)}%`;
}

function describeHabit(state) {
  if (state === DONE) return copy.done;
  return state === MISSED ? copy.missed : copy.untracked;
}

function renderHabit(habit, start) {
  const section = document.createElement("section");
  section.className = "habit";
  section.style.setProperty("--habit-color", habit.color);
  const red = parseInt(habit.color.slice(1, 3), 16);
  const green = parseInt(habit.color.slice(3, 5), 16);
  const blue = parseInt(habit.color.slice(5, 7), 16);
  const brightness = (red * 299 + green * 587 + blue * 114) / 1000;
  section.style.setProperty("--habit-ink", brightness > 140 ? "#1d1720" : "#ffffff");

  const title = document.createElement("h2");
  title.textContent = habit.name;

  const stats = document.createElement("p");
  stats.className = "stats";
  for (const [label, value] of [
    [copy.streak, habit.current_streak],
    [copy.record, habit.longest_streak],
    [copy.total, habit.total_done],
    [copy.completion, `${Math.round(habit.completion_rate * 100)}%`],
  ]) {
    const item = document.createElement("span");
    item.className = "stat";
    const statLabel = document.createElement("span");
    statLabel.className = "stat-label";
    statLabel.textContent = `${label}:`;
    const statValue = document.createElement("strong");
    statValue.className = "stat-value";
    statValue.textContent = value;
    item.append(statLabel, statValue);
    stats.append(item);
  }

  section.append(title, stats, ...renderVisualizations(start, habit.days, habitLevel, describeHabit));
  return section;
}

function renderDashboard(data) {
  const summary = document.createElement("div");
  summary.className = "today-summary";
  const completed = data.habits.filter((habit) => habit.days.at(-1) === DONE).length;
  const percentage = document.createElement("strong");
  percentage.textContent = data.habits.length ? `${Math.round(completed / data.habits.length * 100)}%` : "—";
  const count = document.createElement("span");
  count.textContent = `${copy.today} · ${completed} ${copy.of} ${data.habits.length}`;
  summary.append(percentage, count);
  $("overall").replaceChildren(
    summary,
    ...renderVisualizations(data.start, data.overall, overallLevel, describeOverall),
  );
  $("habits").replaceChildren(...data.habits.map((habit) => renderHabit(habit, data.start)));
  for (const scroll of document.querySelectorAll(".grid-scroll")) {
    scroll.scrollLeft = scroll.scrollWidth;
  }
}

async function showDashboard() {
  $("dashboard").hidden = false;
  $("logout").addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" });
    location.reload();
  });
  try {
    renderDashboard(await api("/api/dashboard"));
  } catch {
    const error = $("dashboard-error");
    error.textContent = copy.data_failed;
    error.hidden = false;
  }
}

async function showLogin() {
  $("login").hidden = false;
  if (new URLSearchParams(location.search).has("error")) {
    $("login-error").hidden = false;
  }
  const { bot_username: botUsername } = await api("/api/config");
  const widget = document.createElement("script");
  widget.async = true;
  widget.src = WIDGET_SRC;
  widget.dataset.telegramLogin = botUsername;
  widget.dataset.size = "large";
  widget.dataset.authUrl = "/api/auth/telegram";
  $("login-widget").append(widget);
}

function showFailure() {
  $("login").hidden = false;
  if (copy) {
    $("login-error").textContent = copy.service_failed;
    $("login-error").hidden = false;
  }
}

try {
  copy = await api("/api/texts");
  $("logout").textContent = copy.logout;
  $("overall-title").textContent = copy.overall;
  $("login-error").textContent = copy.login_failed;
  await api("/api/me");
  await showDashboard();
} catch (error) {
  if (error.status !== 401) {
    showFailure();
  } else {
    try {
      await showLogin();
    } catch {
      showFailure();
    }
  }
}
