export const $ = (id) => document.getElementById(id);
export const toast = (message) => {
  $("toast").textContent = message;
  $("toast").classList.add("show");
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(
    () => $("toast").classList.remove("show"),
    6000,
  );
};
export async function api(url, data, method = "POST", signal) {
  const csrf = document.cookie
    .split("; ")
    .find((x) => x.startsWith("csrftoken="))
    ?.split("=")[1];
  const response = await fetch(url, {
    method,
    signal,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf || "" },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  const type = response.headers.get("content-type") || "";
  const result = type.includes("json") ? await response.json() : null;
  if (!response.ok)
    throw Error(
      result?.error?.message || `Request failed (${response.status})`,
    );
  return result;
}
export function download(name, value) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const theme = localStorage.getItem("argus-theme") || "dark";
document.documentElement.dataset.theme = theme;
$("theme").onclick = () => {
  const t =
    document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = t;
  localStorage.setItem("argus-theme", t);
};
$("help").onclick = () => $("help-dialog").showModal();
document
  .querySelectorAll("[data-close]")
  .forEach((b) => (b.onclick = () => b.closest("dialog").close()));
$("open-reports").onclick = async () => {
  $("reports-dialog").showModal();
  const box = $("report-list");
  box.replaceChildren();
  try {
    const { reports } = await api("/api/v1/reports", undefined, "GET");
    if (!reports.length)
      box.textContent = "No saved investigations in this browser session.";
    for (const r of reports) {
      const article = document.createElement("article");
      const title = document.createElement("h3");
      title.textContent = r.title + " · revision " + r.revision;
      article.append(title);
      const date = document.createElement("p");
      date.textContent = new Date(r.created).toLocaleString();
      article.append(date);
      const open = document.createElement("a");
      open.href = "/reports/" + r.id;
      open.textContent = "Open report ↗";
      open.style.marginRight = "15px";
      article.append(open);
      for (const [label, fn] of [
        [
          "Export JSON",
          async () => {
            const data = await api("/api/v1/reports/" + r.id, undefined, "GET");
            download("argus-" + r.id + ".json", data);
            toast(
              "Immutable report exported with evidence and original-data links.",
            );
          },
        ],
        [
          "Create read link",
          async () => {
            const s = await api("/api/v1/reports/" + r.id + "/shares", {});
            await navigator.clipboard.writeText(location.origin + s.url);
            toast("Read-only report link copied.");
          },
        ],
        [
          "Revoke read links",
          async () => {
            await api("/api/v1/reports/" + r.id + "/shares", {}, "DELETE");
            toast("All read links for this report revoked.");
          },
        ],
      ]) {
        const b = document.createElement("button");
        b.textContent = label;
        b.onclick = () => fn().catch((e) => toast(e.message));
        article.append(b);
      }
      box.append(article);
    }
  } catch (e) {
    box.textContent = e.message;
  }
};
