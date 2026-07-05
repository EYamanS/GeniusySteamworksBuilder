
let STATE = { config: {}, profiles: [], contentBuilderOk: false, contentBuilderMsgKey: "", contentBuilderMsgParams: {} };
let selectedId = null;
let building = false;

const $ = (id) => document.getElementById(id);

function api() { return window.pywebview.api; }

function capsuleUrl(appID) {
    return `https://cdn.cloudflare.steamstatic.com/steam/apps/${appID}/library_600x900_2x.jpg`;
}
function heroUrl(appID) {
    return `https://cdn.cloudflare.steamstatic.com/steam/apps/${appID}/library_hero.jpg`;
}

window.addEventListener("pywebviewready", init);

async function init() {
    applyStaticTranslations();
    bindLangSwitch();
    STATE = await api().get_state();
    renderLibrary();
    if (!STATE.contentBuilderOk || !STATE.config.steamUsername) {
        openSettings();
    }
    bindGlobal();
    bindWindowControls();
}

function bindWindowControls() {
    $("winMinBtn").onclick = () => api().win_minimize();
    $("winCloseBtn").onclick = () => api().win_close();
    const toggleMax = () => api().win_toggle_maximize();
    $("winMaxBtn").onclick = toggleMax;
    $("titlebarDrag").addEventListener("dblclick", toggleMax);
    bindResizeHandles();
}

function bindResizeHandles() {
    document.querySelectorAll(".rz").forEach((h) => {
        h.addEventListener("mousedown", (e) => {
            if (e.button !== 0) return;
            e.preventDefault();
            api().start_resize(h.dataset.edge);
        });
    });
}

function bindLangSwitch() {
    const btn = $("langBtn");
    const menu = $("langMenu");
    btn.onclick = (e) => { e.stopPropagation(); menu.classList.toggle("hidden"); markActiveLang(); };
    document.addEventListener("click", () => menu.classList.add("hidden"));
    menu.querySelectorAll(".lang-opt").forEach((opt) => {
        opt.onclick = (e) => {
            e.stopPropagation();
            setLang(opt.dataset.lang);
            menu.classList.add("hidden");
        };
    });
    markActiveLang();
}

function markActiveLang() {
    $("langMenu").querySelectorAll(".lang-opt").forEach((opt) => {
        opt.classList.toggle("active", opt.dataset.lang === LANG);
    });
}

function onLangChange() {
    markActiveLang();
    renderLibrary();
    if (current()) renderDepots();
    if ($("settingsModal") && !$("settingsModal").classList.contains("hidden")) {
        updateCbStatus();
        $("pwStatus").textContent = STATE.config.hasPassword ? t("pwSaved") : t("pwNotSaved");
    }
}

function bindGlobal() {
    $("importBtn").onclick = importExisting;
    bindDeleteAll();
    $("settingsBtn").onclick = openSettings;
    $("emptyNewGameBtn").onclick = openNewGameModal;

    $("backBtn").onclick = showLibrary;

    $("browseCbBtn").onclick = browseContentBuilder;
    $("saveSettingsBtn").onclick = saveSettings;
    $("cancelSettingsBtn").onclick = closeSettings;
    $("closeSettingsBtn").onclick = closeSettings;
    $("clearPwBtn").onclick = clearPassword;

    $("createGameBtn").onclick = createGame;
    $("cancelNewGameBtn").onclick = closeNewGameModal;
    $("closeNewGameBtn").onclick = closeNewGameModal;
    $("ngBrowseBtn").onclick = async () => {
        const folder = await api().pick_folder($("ngFolder").value);
        if (folder) $("ngFolder").value = folder;
    };
    $("ngName").addEventListener("keydown", (e) => { if (e.key === "Enter") createGame(); });
    $("ngAppID").addEventListener("keydown", (e) => { if (e.key === "Enter") createGame(); });

    $("deleteProfileBtn").onclick = deleteProfile;
    $("deleteGameNoBtn").onclick = closeDeleteGameModal;
    $("deleteGameYesBtn").onclick = confirmDeleteGame;
    $("addDepotBtn").onclick = () => { addDepot(); };
    $("buildBtn").onclick = () => runBuild(false);
    $("previewBuildBtn").onclick = () => runBuild(true);
    $("openContentBtn").onclick = openContentFolder;
    $("partnerBtn").onclick = openPartner;

    $("clearConsoleBtn").onclick = () => { $("console").innerHTML = ""; };
    $("cancelBuildBtn").onclick = () => api().cancel_build();
    $("closeConsoleBtn").onclick = () => {
        $("console").innerHTML = "";
        $("consolePanel").classList.add("hidden");
        setConsoleDone(false);
    };

    $("submitGuardBtn").onclick = submitGuard;
    $("guardCode").addEventListener("keydown", (e) => { if (e.key === "Enter") submitGuard(); });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeNewGameModal();
            closeSettings();
            closeDeleteAllModal();
        }
    });

    ["pName", "pAppID", "pBranch", "pDesc"].forEach((id) => {
        $(id).addEventListener("change", collectAndSave);
    });
    $("pAppID").addEventListener("change", () => { const p = current(); if (p) updateHero(p); });
}

function current() { return STATE.profiles.find((p) => p.id === selectedId); }

function renderLibrary() {
    const grid = $("gameGrid");
    grid.innerHTML = "";
    const has = STATE.profiles.length > 0;
    $("emptyLibrary").classList.toggle("hidden", has);
    grid.classList.toggle("hidden", !has);
    if (!has) return;

    STATE.profiles.forEach((p) => {
        const card = document.createElement("div");
        card.className = "game-card";
        const name = p.name || t("unnamed");
        const depotCount = (p.depots || []).length;

        const fallback = document.createElement("div");
        fallback.className = "card-fallback";
        fallback.textContent = (name.trim()[0] || "?").toUpperCase();
        card.appendChild(fallback);

        if (p.appID) {
            const img = document.createElement("img");
            img.className = "card-img";
            img.loading = "lazy";
            img.src = capsuleUrl(p.appID);
            img.addEventListener("error", () => img.remove());
            card.appendChild(img);
        }

        const label = document.createElement("div");
        label.className = "card-name";
        label.innerHTML = `${esc(name)}<span class="card-meta">${esc(t("profileMeta", { appID: p.appID || "?", n: depotCount }))}</span>`;
        card.appendChild(label);

        const del = document.createElement("button");
        del.className = "card-del";
        del.title = t("deleteGame");
        del.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path><path d="M10 11v6M14 11v6"></path><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path></svg>`;
        del.onclick = (e) => { e.stopPropagation(); openDeleteGameModal(p.id); };
        card.appendChild(del);

        card.onclick = () => openGame(p.id);
        grid.appendChild(card);
    });

    const add = document.createElement("button");
    add.className = "new-game-card";
    add.innerHTML = `<span class="plus">+</span><span>${esc(t("newGame_card"))}</span>`;
    add.onclick = openNewGameModal;
    grid.appendChild(add);
}

function showLibrary() {
    if (building) { toast(t("cantSwitchBuilding"), "bad"); return; }
    selectedId = null;
    renderLibrary();
    $("gameView").classList.add("hidden");
    const lib = $("libraryView");
    lib.classList.remove("hidden");
    restartAnim(lib);
}

function openGame(id) {
    selectedId = id;
    const p = current();
    if (!p) return;
    $("libraryView").classList.add("hidden");
    const gv = $("gameView");
    gv.classList.remove("hidden");
    restartAnim(gv);

    $("pName").value = p.name || "";
    $("pAppID").value = p.appID || "";
    $("pBranch").value = p.branch || "";
    $("pDesc").value = p.description || "";
    updateHero(p);
    renderDepots();
}

function restartAnim(el) {
    el.style.animation = "none";
    void el.offsetHeight;
    el.style.animation = "";
}

function updateHero(p) {
    const bg = $("heroBg");
    if (p.appID) {
        const url = heroUrl(p.appID);
        const probe = new Image();
        probe.onload = () => { bg.style.backgroundImage = `url("${url}")`; };
        probe.onerror = () => { bg.style.backgroundImage = "none"; };
        probe.src = url;
    } else {
        bg.style.backgroundImage = "none";
    }
}

function openNewGameModal() {
    $("ngName").value = "";
    $("ngAppID").value = "";
    $("ngFolder").value = "";
    $("newGameModal").classList.remove("hidden");
    $("ngName").focus();
}
function closeNewGameModal() { $("newGameModal").classList.add("hidden"); }

function createGame() {
    const name = $("ngName").value.trim();
    const appID = $("ngAppID").value.trim();
    const folder = $("ngFolder").value.trim();
    if (!name) { toast(t("err_ng_name"), "bad"); $("ngName").focus(); return; }
    if (!appID) { toast(t("err_no_appid"), "bad"); $("ngAppID").focus(); return; }

    const guessedDepot = /^\d+$/.test(appID) ? String(Number(appID) + 1) : "";

    const p = {
        id: "tmp_" + Date.now(),
        name, appID,
        description: "", branch: "", preview: false,
        depots: [{ depotID: guessedDepot, contentPath: folder, exclusions: ["*.pdb"] }],
    };
    STATE.profiles.push(p);
    persist();
    closeNewGameModal();
    openGame(p.id);
    toast(t("gameAdded", { name }), "ok");
}

function deleteProfile() {
    const p = current();
    if (!p) return;
    openDeleteGameModal(p.id);
}

let pendingDeleteId = null;
function openDeleteGameModal(id) {
    pendingDeleteId = id;
    $("deleteGameModal").classList.remove("hidden");
}
function closeDeleteGameModal() {
    pendingDeleteId = null;
    $("deleteGameModal").classList.add("hidden");
}
function confirmDeleteGame() {
    const id = pendingDeleteId;
    closeDeleteGameModal();
    if (!id) return;
    STATE.profiles = STATE.profiles.filter((x) => x.id !== id);
    if (selectedId === id) selectedId = null;
    persist();
    showLibrary();
}

function renderDepots() {
    const p = current();
    const box = $("depotList");
    box.innerHTML = "";
    (p.depots || []).forEach((d, i) => {
        const card = document.createElement("div");
        card.className = "depot-card";
        card.innerHTML = `
            <div class="depot-card-head">
                <span class="dc-title">${esc(t("depotTitle", { n: i + 1 }))}</span>
                <button class="btn btn-ghost btn-xs danger-text" data-rm="${i}">${esc(t("remove"))}</button>
            </div>
            <div class="depot-grid">
                <div class="field" style="margin:0">
                    <label>${esc(t("depotId"))}</label>
                    <input type="text" data-f="depotID" data-i="${i}" value="${esc(d.depotID || "")}" placeholder="${esc(t("depotId_ph"))}">
                </div>
                <div class="field" style="margin:0">
                    <label>${esc(t("contentFolder"))} <span class="detected-exe" data-exe="${i}"></span></label>
                    <div class="path-row">
                        <input type="text" data-f="contentPath" data-i="${i}" value="${esc(d.contentPath || "")}" placeholder="${esc(t("contentFolder_ph"))}">
                        <button class="btn btn-ghost btn-sm" data-browse="${i}">${esc(t("browse"))}</button>
                    </div>
                </div>
            </div>
            <div class="field" style="margin:10px 0 0">
                <label>${esc(t("exclusions"))} <span class="hint">${esc(t("exclusions_hint"))}</span></label>
                <input type="text" data-f="exclusions" data-i="${i}" value="${esc((d.exclusions || []).join(", "))}" placeholder="${esc(t("exclusions_ph"))}">
            </div>`;
        box.appendChild(card);
    });

    box.querySelectorAll("input[data-f]").forEach((inp) => {
        inp.addEventListener("change", () => {
            const i = +inp.dataset.i, f = inp.dataset.f;
            const p2 = current();
            if (f === "exclusions") {
                p2.depots[i].exclusions = inp.value.split(",").map((s) => s.trim()).filter(Boolean);
            } else {
                p2.depots[i][f] = inp.value.trim();
            }
            persist();
        });
    });
    box.querySelectorAll("[data-rm]").forEach((b) => {
        b.onclick = () => {
            const i = +b.dataset.rm;
            current().depots.splice(i, 1);
            persist(); renderDepots();
        };
    });
    box.querySelectorAll("[data-browse]").forEach((b) => {
        b.onclick = async () => {
            const i = +b.dataset.browse;
            const start = current().depots[i].contentPath || STATE.config.contentBuilderPath || "";
            const folder = await api().pick_folder(start);
            if (folder) { current().depots[i].contentPath = folder; persist(); renderDepots(); }
        };
    });

    refreshDetectedExes();
}

async function refreshDetectedExes() {
    const p = current();
    if (!p) return;
    await Promise.all((p.depots || []).map(async (d, i) => {
        const span = document.querySelector(`.detected-exe[data-exe="${i}"]`);
        if (!span) return;
        span.textContent = "";
        if (!d.contentPath) return;
        try {
            const name = await api().detect_exe(d.contentPath);
            if (name) span.textContent = `(${t("detectedExe", { name })})`;
        } catch (e) {  }
    }));
}

function addDepot() {
    current().depots.push({ depotID: "", contentPath: "", exclusions: ["*.pdb"] });
    persist(); renderDepots();
}

function collectAndSave() {
    const p = current();
    if (!p) return;
    p.name = $("pName").value;
    p.appID = $("pAppID").value.trim();
    p.branch = $("pBranch").value.trim();
    p.description = $("pDesc").value;
    persist();
}

async function persist() {
    await api().save_profiles(STATE.profiles);
}

async function importExisting() {
    const r = await api().import_existing();
    if (!r.ok) { toast(t(r.msgKey, r.params), "bad"); return; }
    STATE = await api().get_state();
    renderLibrary();
    toast(t(r.msgKey, r.params), r.count > 0 ? "ok" : null);
}

const DELETE_HOLD_MS = 3000;
let holdRAF = null;
let holdStart = 0;

function bindDeleteAll() {
    const btn = $("deleteAllBtn");
    btn.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        try { btn.setPointerCapture(e.pointerId); } catch (_) {}
        startDeleteHold();
    });
    btn.addEventListener("pointerup", () => cancelDeleteHold(false));
    btn.addEventListener("pointercancel", () => cancelDeleteHold(false));
    btn.addEventListener("lostpointercapture", () => cancelDeleteHold(false));

    $("deleteAllNoBtn").onclick = closeDeleteAllModal;
    $("deleteAllYesBtn").onclick = confirmDeleteAll;
}

function startDeleteHold() {
    if (holdRAF) return;
    const btn = $("deleteAllBtn");
    btn.classList.add("holding");
    holdStart = performance.now();
    holdRAF = requestAnimationFrame(tickDeleteHold);
}

function tickDeleteHold() {
    const btn = $("deleteAllBtn");
    const fill = btn.querySelector(".da-fill");
    const p = Math.min((performance.now() - holdStart) / DELETE_HOLD_MS, 1);

    fill.style.width = (p * 100) + "%";
    const scale = 1 + p * 0.28;
    const amp = p * 3.5;
    const dx = (Math.random() * 2 - 1) * amp;
    const dy = (Math.random() * 2 - 1) * amp;
    btn.style.transform = `translate(${dx}px, ${dy}px) scale(${scale})`;

    if (p >= 1) { cancelDeleteHold(true); return; }
    holdRAF = requestAnimationFrame(tickDeleteHold);
}

function cancelDeleteHold(completed) {
    if (holdRAF) { cancelAnimationFrame(holdRAF); holdRAF = null; }
    const btn = $("deleteAllBtn");
    btn.classList.remove("holding");
    btn.style.transform = "";
    btn.querySelector(".da-fill").style.width = "0%";
    if (completed) openDeleteAllModal();
}

function openDeleteAllModal() { $("deleteAllModal").classList.remove("hidden"); }
function closeDeleteAllModal() { $("deleteAllModal").classList.add("hidden"); }

async function confirmDeleteAll() {
    STATE.profiles = [];
    selectedId = null;
    await persist();
    closeDeleteAllModal();
    showLibrary();
    toast(t("allGamesDeleted"), "ok");
}

function openSettings() {
    $("sContentBuilder").value = STATE.config.contentBuilderPath || "";
    $("sUsername").value = STATE.config.steamUsername || "";
    $("sPassword").value = "";
    updateCbStatus();
    $("pwStatus").textContent = STATE.config.hasPassword ? t("pwSaved") : t("pwNotSaved");
    $("pwStatus").className = "path-status " + (STATE.config.hasPassword ? "ok" : "");
    $("settingsModal").classList.remove("hidden");
}
function closeSettings() { $("settingsModal").classList.add("hidden"); }

function updateCbStatus() {
    const ok = STATE.contentBuilderOk;
    const el = $("cbStatus");
    el.textContent = ok ? t("steamcmdFound") : (STATE.contentBuilderMsgKey ? t(STATE.contentBuilderMsgKey, STATE.contentBuilderMsgParams) : "");
    el.className = "path-status " + (ok ? "ok" : "bad");
}

async function browseContentBuilder() {
    const folder = await api().pick_folder($("sContentBuilder").value);
    if (folder) $("sContentBuilder").value = folder;
}

async function saveSettings() {
    STATE = await api().save_settings(
        $("sContentBuilder").value,
        $("sUsername").value,
        $("sPassword").value
    );
    updateCbStatus();
    renderLibrary();
    if (STATE.contentBuilderOk) {
        toast(t("settingsSaved"), "ok");
        closeSettings();
    } else {
        toast(t(STATE.contentBuilderMsgKey, STATE.contentBuilderMsgParams), "bad");
    }
}

async function clearPassword() {
    STATE = await api().clear_password();
    $("pwStatus").textContent = t("pwDeletedStatus");
    $("pwStatus").className = "path-status";
    toast(t("pwDeleted"), null);
}

async function runBuild(preview) {
    const p = current();
    if (!p) return;
    collectAndSave();

    $("consolePanel").classList.remove("hidden");
    if (!preview) $("console").innerHTML = "";
    setConsoleDone(false);
    setStatus("running", t("starting"));
    building = true;
    setBuildingUI(true);

    const r = await api().start_build(p, preview);
    if (!r.ok) {
        const msg = t(r.msgKey, r.params);
        appendConsole("error", t("startErrLine", { msg }));
        setStatus("error", t("startFailed"));
        building = false;
        setBuildingUI(false);
        toast(msg, "bad");
    } else {
        setStatus("running", preview ? t("previewRunning") : t("buildRunning"));
    }
}

function setBuildingUI(on) {
    $("buildBtn").disabled = on;
    $("previewBuildBtn").disabled = on;
}

function setConsoleDone(done) {
    $("clearConsoleBtn").classList.toggle("hidden", done);
    $("cancelBuildBtn").classList.toggle("hidden", done);
    $("closeConsoleBtn").classList.toggle("hidden", !done);
}

window.onBuildOutput = (kind, text) => {
    appendConsole(kind, text);
};
window.onGuardNeeded = (line) => {
    $("guardPrompt").textContent = line.trim() || t("guardPrompt");
    $("guardCode").value = "";
    $("guardModal").classList.remove("hidden");
    $("guardCode").focus();
};
window.onBuildDone = (success, code) => {
    building = false;
    setBuildingUI(false);
    setConsoleDone(true);
    if (success) {
        setStatus("success", t("buildSuccess"));
        appendConsole("success", t("buildDoneLine", { code }));
        toast(t("buildSuccessToast"), "ok");
    } else {
        setStatus("error", t("buildFailStatus", { code }));
        appendConsole("error", t("buildFailLine", { code }));
        toast(t("buildFailToast"), "bad");
    }
};

function submitGuard() {
    const code = $("guardCode").value.trim();
    if (!code) return;
    api().submit_guard_code(code);
    $("guardModal").classList.add("hidden");
}

function setStatus(cls, text) {
    const el = $("buildStatus");
    el.className = "build-status " + cls;
    el.textContent = text;
}

function appendConsole(kind, text) {
    const con = $("console");
    const span = document.createElement("span");
    span.className = "l-" + kind;
    span.textContent = text;
    con.appendChild(span);
    con.scrollTop = con.scrollHeight;
}

async function openContentFolder() {
    const p = current();
    const first = (p.depots || []).find((d) => d.contentPath);
    if (first) await api().open_path(first.contentPath);
    else toast(t("noContentFolder"), "bad");
}
function openPartner() {
    const p = current();
    if (p && p.appID) api().open_partner_page(p.appID);
    else toast(t("err_no_appid"), "bad");
}

function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => (
        { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
}

let toastTimer = null;
function toast(msg, kind) {
    const t = $("toast");
    t.textContent = msg;
    t.className = "toast" + (kind ? " " + kind : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.add("hidden"), 3500);
}
