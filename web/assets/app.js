const WIDGET_SRC = "https://telegram.org/js/telegram-widget.js?22";
const MONTHS = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
const DONE = 2;
const MISSED = 1;

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
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
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

function describeOverall(ratio) {
  return ratio === null ? "нет привычек" : `${Math.round(ratio * 100)}%`;
}

function describeHabit(state) {
  if (state === DONE) return "выполнено";
  return state === MISSED ? "пропущено" : "не отслеживалось";
}

function renderHabit(habit, start) {
  const section = document.createElement("section");
  section.className = "habit";

  const title = document.createElement("h2");
  title.textContent = habit.name;

  const stats = document.createElement("p");
  stats.className = "stats";
  for (const text of [
    `Серия: ${habit.current_streak}`,
    `Рекорд: ${habit.longest_streak}`,
    `Всего: ${habit.total_done}`,
    `Выполнение: ${Math.round(habit.completion_rate * 100)}%`,
  ]) {
    const item = document.createElement("span");
    item.textContent = text;
    stats.append(item);
  }

  section.append(title, stats, renderGrid(start, habit.days, habitLevel, describeHabit));
  return section;
}

function renderDashboard(data) {
  $("overall").replaceChildren(renderGrid(data.start, data.overall, overallLevel, describeOverall));
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
    error.textContent = "Не удалось загрузить данные.";
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
  $("login-error").textContent = "Сервис недоступен. Попробуйте позже.";
  $("login-error").hidden = false;
}

try {
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
