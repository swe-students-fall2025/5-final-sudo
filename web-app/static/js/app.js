// ======== GLOBAL STATE ========
let allDocuments = [];

// ======== SIMPLE HELPERS ========
function importanceLabel(raw) {
    // backend might store numeric (2–5) or string
    if (typeof raw === "number") {
        return { 2: "Low", 3: "Medium", 4: "High", 5: "Critical" }[raw] || "Medium";
    }
    return raw || "Medium";
}

function importanceColor(label) {
    return {
        Critical: "bg-red-100 text-red-700 border-red-200",
        High: "bg-orange-100 text-orange-700 border-orange-200",
        Medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
        Low: "bg-green-100 text-green-700 border-green-200",
    }[label] || "bg-gray-100 text-gray-700 border-gray-200";
}

function expiryStatus(expiryDate, leadTimeDays) {
    const expiry = new Date(expiryDate);
    const today = new Date();
    const days = Math.ceil((expiry - today) / 86400000);

    if (isNaN(days)) {
        return {
            status: "Unknown",
            color: "bg-gray-50 border-gray-200 text-gray-600",
            icon: "❔",
            days,
        };
    }

    if (days < 0) {
        return {
            status: "Expired",
            color: "bg-red-50 border-red-200 text-red-700",
            icon: "🔴",
            days,
        };
    }

    if (days <= leadTimeDays) {
        return {
            status: "Action Needed",
            color: "bg-orange-50 border-orange-200 text-orange-700",
            icon: "⚠️",
            days,
        };
    }

    if (days <= leadTimeDays * 2) {
        return {
            status: "Upcoming",
            color: "bg-yellow-50 border-yellow-200 text-yellow-700",
            icon: "🟡",
            days,
        };
    }

    return {
        status: "Active",
        color: "bg-green-50 border-green-200 text-green-700",
        icon: "✅",
        days,
    };
}

function formatDate(dateStr) {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr || "";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function iconForType(type) {
    const map = {
        Passport: "🛂",
        Visa: "💳",
        License: "🪪",
        Permit: "📜",
        Warranty: "🧾",
        Insurance: "🛡️",
        Membership: "🏅",
        Certification: "📘",
    };
    return map[type] || "📄";
}

// ======== CARD RENDERING ========
function renderCard(doc) {
    const type = doc.doc_type || doc.type || "";
    const label = importanceLabel(doc.importance);
    const lead = doc.renewal_lead_time_days ?? doc.leadTimeDays ?? 0;
    const status = expiryStatus(doc.expiry_date || doc.expiryDate, lead);

    return `
<div class="group relative bg-white rounded-lg border border-gray-200 hover:shadow-lg transition-all duration-200 hover:-translate-y-1 overflow-hidden p-5 space-y-4">
    <div class="flex items-start justify-between gap-3">
        <div class="flex items-center gap-3 flex-1 min-w-0">
            <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-lg">
                ${iconForType(type)}
            </div>
            <div class="flex-1 min-w-0">
                <h3 class="truncate text-gray-900 font-semibold">${doc.name || ""}</h3>
                <p class="text-gray-500 text-sm">${type}</p>
            </div>
        </div>
        <button onclick="deleteDocument('${doc.id}')"
                        class="opacity-0 group-hover:opacity-100 transition-opacity p-2 hover:bg-gray-100 rounded-md text-gray-400 hover:text-red-600 text-sm">
            🗑️
        </button>
    </div>

    <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs ${status.color}">
        <span>${status.icon}</span>
        <span>${status.status}</span>
        ${!isNaN(status.days) ? `<span class="text-gray-500 ml-1">(${status.days} days)</span>` : ""}
    </div>

    <div class="space-y-3 text-sm mt-2">
        ${doc.label ? `
        <div class="flex items-center gap-2">
            <span class="text-gray-600">Label:</span>
            <span class="bg-blue-50 border border-blue-200 text-blue-700 px-2 py-0.5 rounded-md text-xs">${doc.label}</span>
        </div>` : ""}

        <div class="flex items-center gap-2">
            <span class="text-gray-600">Expires:</span>
            <span class="text-gray-900">${formatDate(doc.expiry_date || doc.expiryDate)}</span>
        </div>

        <div class="flex items-center gap-2">
            <span class="text-gray-600">Lead Time:</span>
            <span class="text-gray-900">${lead} days</span>
        </div>

        <div class="flex items-center gap-2">
            <span class="text-gray-600">Importance:</span>
            <span class="border px-2 py-0.5 rounded-md text-xs ${importanceColor(label)}">
                ${label}
            </span>
        </div>

        ${doc.notes ? `
        <div class="pt-2 border-t border-gray-100">
            <p class="text-gray-600 text-xs">${doc.notes}</p>
        </div>` : ""}
    </div>
</div>`;
}

// ======== RENDER LIST, FILTERS, STATS ========
function renderDocumentList() {
    const listEl = document.getElementById("documentList");
    if (!listEl) return;

    const search = (document.getElementById("searchInput")?.value || "").toLowerCase();
    const typeFilter = document.getElementById("filterType")?.value || "all";
    const impFilter = document.getElementById("filterImportance")?.value || "all";

    // filter docs
    const filtered = allDocuments.filter((doc) => {
        const name = (doc.name || "").toLowerCase();
        const type = (doc.doc_type || doc.type || "").toLowerCase();
        const label = (doc.label || "").toLowerCase();
        const textMatch = name.includes(search) || type.includes(search) || label.includes(search);

        const typeOk = typeFilter === "all" || (doc.doc_type || doc.type) === typeFilter;
        const impLabel = importanceLabel(doc.importance);
        const impOk = impFilter === "all" || impLabel === impFilter;

        return textMatch && typeOk && impOk;
    });

    // stats
    const criticalCount = allDocuments.filter((d) => importanceLabel(d.importance) === "Critical").length;

    const expiringCount = allDocuments.filter((d) => {
        const status = expiryStatus(d.expiry_date || d.expiryDate, d.renewal_lead_time_days ?? d.leadTimeDays ?? 0);
        return status.status === "Action Needed";
    }).length;

    const statTotal = document.getElementById("statTotal");
    const statExpiring = document.getElementById("statExpiring");
    const statCritical = document.getElementById("statCritical");
    const boxExpiring = document.getElementById("statExpiringBox");
    const boxCritical = document.getElementById("statCriticalBox");

    if (statTotal) statTotal.textContent = allDocuments.length.toString();
    if (statExpiring && boxExpiring) {
        statExpiring.textContent = expiringCount.toString();
        boxExpiring.classList.toggle("hidden", expiringCount === 0);
    }
    if (statCritical && boxCritical) {
        statCritical.textContent = criticalCount.toString();
        boxCritical.classList.toggle("hidden", criticalCount === 0);
    }

    // update type filter options
    const typeSelect = document.getElementById("filterType");
    if (typeSelect && typeSelect.options.length === 1) {
        const types = [...new Set(allDocuments.map((d) => d.doc_type || d.type))].filter(Boolean);
        types.forEach((t) => {
            const opt = document.createElement("option");
            opt.value = t;
            opt.textContent = t;
            typeSelect.appendChild(opt);
        });
    }

    if (filtered.length === 0) {
        listEl.innerHTML = `
            <div class="col-span-full text-center py-16">
                <div class="w-16 h-16 bg-white border border-gray-300 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span class="text-2xl text-gray-400">📄</span>
                </div>
                <h3 class="text-gray-900 mb-2">No documents found</h3>
                <p class="text-gray-600 text-sm">
                    ${search || typeFilter !== "all" || impFilter !== "all"
                        ? "Try adjusting your search or filters."
                        : "Get started by adding your first document."}
                </p>
            </div>`;
        return;
    }

    listEl.innerHTML = filtered.map(renderCard).join("");
}

// ======== API: LOAD / ADD / DELETE ========
async function loadDocuments() {
    const res = await fetch("/api/documents");
    const docs = await res.json();
    allDocuments = docs;
    renderDocumentList();
}

async function deleteDocument(id) {
    if (!confirm("Delete this document?")) return;
    const res = await fetch(`/api/documents/${id}`, { method: "DELETE" });
    if (res.ok) {
        allDocuments = allDocuments.filter((d) => d.id !== id);
        renderDocumentList();
    } else {
        alert("Error deleting document");
    }
}

window.deleteDocument = deleteDocument; // so inline onclick works

function resetForm() {
    document.getElementById("addForm")?.reset();
}

// ======== AUTH ========
async function checkAuth() {
    const res = await fetch("/api/auth/me");
    const data = await res.json();
    if (data.logged_in) showDashboard();
    else showAuth();
}

function showDashboard() {
    disableAuthLayout();
    document.getElementById("authPanel")?.classList.add("hidden");
    document.getElementById("dashboard")?.classList.remove("hidden");
    loadDocuments();
}

function showAuth() {
    enableAuthLayout();
    document.getElementById("authPanel")?.classList.remove("hidden");
    document.getElementById("dashboard")?.classList.add("hidden");
    const list = document.getElementById("documentList");
    if (list) list.innerHTML = "";
}

async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    showAuth();
}
window.logout = logout;

function enableAuthLayout() {
    const el = document.getElementById("bodyEl");
    el.classList.add("flex", "items-center", "justify-center");
}

function disableAuthLayout() {
    const el = document.getElementById("bodyEl");
    el.classList.remove("flex", "items-center", "justify-center");
}

function openModal() {
    document.getElementById("docModal")?.classList.remove("hidden");
    document.getElementById("docModalBackdrop")?.classList.remove("hidden");
}

function closeModal() {
    document.getElementById("docModal")?.classList.add("hidden");
    document.getElementById("docModalBackdrop")?.classList.add("hidden");
}

function downloadCalendar() {
    // Download the calendar file
    window.location.href = "/api/documents/calendar.ics";
}
window.downloadCalendar = downloadCalendar;

// ======== EVENT WIRING ========
document.addEventListener("DOMContentLoaded", () => {
    // login
    const loginForm = document.getElementById("loginForm");
    loginForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("loginEmail")?.value || "";
        const password = document.getElementById("loginPassword")?.value || "";

        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });

        if (res.ok) {
            loginForm.reset();
            showDashboard();
        } else {
            const data = await res.json();
            alert("Login failed: " + (data.error || "Unknown error"));
        }
    });

    // register
    const regForm = document.getElementById("registerForm");
    regForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("regEmail")?.value || "";
        const password = document.getElementById("regPassword")?.value || "";

        const res = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });

        const data = await res.json();
        if (res.ok) {
            alert("Account created and logged in!");
            regForm.reset();
            showDashboard();
        } else {
            alert("Registration failed: " + (data.error || "Unknown error"));
        }
    });

    // add doc
    const addForm = document.getElementById("addForm");
    addForm?.addEventListener("submit", async (e) => {
        e.preventDefault();

        const docType = document.getElementById("doc_type")?.value || "";
        const name = document.getElementById("name")?.value || "";
        const label = document.getElementById("label")?.value || null;
        const expiry = document.getElementById("expiry_date")?.value || "";
        const lead = parseInt(document.getElementById("lead_time")?.value || "0", 10);
        const importanceVal = document.getElementById("importance")?.value || "";
        const notes = document.getElementById("notes")?.value || null;

        const payload = {
            doc_type: docType,
            name,
            label,
            expiry_date: expiry,
            renewal_lead_time_days: lead,
            importance: importanceVal || null,
            notes,
        };

        const res = await fetch("/api/documents", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (res.ok) {
            addForm.reset();
            await loadDocuments();
        } else {
            alert("Error adding document");
        }
    });

    // filters re-render
    document.getElementById("searchInput")?.addEventListener("input", renderDocumentList);
    document.getElementById("filterType")?.addEventListener("change", renderDocumentList);
    document.getElementById("filterImportance")?.addEventListener("change", renderDocumentList);

    // initial auth check
    checkAuth();
});
