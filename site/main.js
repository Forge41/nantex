const INSTALL = {
  uvx: { cmd: "uvx nantex main.tex", note: "Runs the latest release in an isolated env. Nothing installed permanently." },
  uv: { cmd: "uv tool install nantex\nnantex main.tex", note: "Puts the nantex command on your PATH via uv." },
  pip: { cmd: "pip install nantex\nnantex main.tex", note: "Works in any venv or global Python 3.11+." },
};

function copy(button, text) {
  navigator.clipboard?.writeText(text).catch(() => {});
  button.textContent = "Copied";
  setTimeout(() => (button.textContent = "Copy"), 1400);
}

document.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", () => copy(b, b.dataset.copy)));

const cmd = document.querySelector("[data-install-cmd]");
const note = document.querySelector("[data-install-note]");
const tabs = document.querySelectorAll("[data-tab]");
tabs.forEach((tab) =>
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.setAttribute("aria-selected", String(t === tab)));
    cmd.textContent = INSTALL[tab.dataset.tab].cmd;
    note.textContent = INSTALL[tab.dataset.tab].note;
  }),
);
document.querySelector("[data-copy-install]").addEventListener("click", (e) => copy(e.currentTarget, cmd.textContent));

document.querySelector("[data-today]").textContent = new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });

fetch("https://pypi.org/pypi/nantex/json")
  .then((r) => (r.ok ? r.json() : Promise.reject()))
  .then((d) => (document.querySelector("[data-version]").textContent = "v" + d.info.version))
  .catch(() => {});
