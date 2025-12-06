// =======================================================
//  GLOBAL STATE
// =======================================================
let allDocuments = [];
let currentEditDocId = null;
let showingArchived = false;

const archivedList = document.getElementById("archivedList");
const archivedSection = document.getElementById("archivedSection");


// =======================================================
//  RISK BADGE (backend-aligned)
// =======================================================
function riskBadge(doc) {
    const risk = doc.risk || "UNKNOWN";
    const days = doc.days_until;

    const colors = {
        CRITICAL: "bg-red-100 text-red-700 border-red-200",
        HIGH:     "bg-orange-100 text-orange-700 border-orange-200",
        MEDIUM:   "bg-yellow-100 text-yellow-700 border-yellow-200",
        LOW:      "bg-green-100 text-green-700 border-green-200",
        UNKNOWN:  "bg-gray-100 text-gray-700 border-gray-200",
    };

    const icons = {
        CRITICAL: "🔴",
        HIGH:     "⚠️",
        MEDIUM:   "🟡",
        LOW:      "🟢",
        UNKNOWN:  "❔",
    };

    return `
        <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs ${colors[risk]}">
            <span>${icons[risk]}</span>
            <span>${risk} RISK</span>
            ${typeof days === "number" ? `<span class="text-gray-500 ml-1">(${days} days left)</span>` : ""}
        </div>
    `;
}





// =======================================================
//  ICON MAP
// =======================================================
function iconForType(type) {
    const map = {
        passport: "🛂",
        visa: "💳",
        driver_license: "🪪",
        permit: "📜",
        warranty: "🧾",
        insurance: "🛡️",
        membership: "🏅",
        certification: "📘",
        subscription: "📱",
        car_registration: "🚗",
        lease: "🏠",
        other: "📄",
    };
    return map[type] || "📄";
}

document.addEventListener("DOMContentLoaded", () => {

  document.querySelectorAll(".custom-select").forEach(select => {
    const trigger = select.querySelector(".select-trigger");
    const menu = select.querySelector(".dropdown-content");
    const valueDisplay = select.querySelector(".select-value");
    const hiddenInput = select.querySelector(".select-input");

    // ---- OPEN / CLOSE LOGIC ----
    trigger.addEventListener("click", () => {
      const isHidden = menu.classList.contains("hidden");

      if (isHidden) {
        // OPEN
        menu.classList.remove("hidden");
        requestAnimationFrame(() => menu.classList.add("open"));
      } else {
        // CLOSE
        menu.classList.remove("open");
        setTimeout(() => menu.classList.add("hidden"), 120);
      }
    });

    // ---- OPTION SELECT ----
    menu.querySelectorAll(".dropdown-option").forEach(opt => {
      opt.addEventListener("click", () => {
        const val = opt.dataset.value;
        const label = opt.textContent;

        hiddenInput.value = val;
        valueDisplay.textContent = label;
        valueDisplay.classList.remove("text-gray-500");

        // Close menu
        menu.classList.remove("open");
        setTimeout(() => menu.classList.add("hidden"), 120);
      });
    });

  });

  // ---- CLICK OUTSIDE TO CLOSE ANY OPEN MENU ----
  document.addEventListener("click", (e) => {
    document.querySelectorAll(".custom-select").forEach(select => {
      const menu = select.querySelector(".dropdown-content");
      if (!menu) return;

      if (!select.contains(e.target)) {
        menu.classList.remove("open");
        setTimeout(() => menu.classList.add("hidden"), 120);
      }
    });
  });

});



// =======================================================
//  UPDATE STATS
// =======================================================
function updateStats(docs) {
    const total = docs.length;
    const expiring = docs.filter(doc =>
        doc.last_risk === "HIGH" || doc.last_risk === "MEDIUM"
    ).length;
    const critical = docs.filter(doc =>
        doc.last_risk === "CRITICAL"
    ).length;

    // Insert text
    document.getElementById("statTotal").textContent = total;
    document.getElementById("statExpiring").textContent = expiring;
    document.getElementById("statCritical").textContent = critical;

    // Show or hide boxes
    const expBox = document.getElementById("statExpiringBox");
    const critBox = document.getElementById("statCriticalBox");

    if (expiring > 0) expBox.classList.remove("hidden");
    else expBox.classList.add("hidden");

    if (critical > 0) critBox.classList.remove("hidden");
    else critBox.classList.add("hidden");
}

// =======================================================
//  FORMAT DATE
// =======================================================
function formatDate(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}


// =======================================================
//  CARD RENDERING
// =======================================================
function renderCard(doc) {
    const type = doc.doc_type || "other";

    return `
<div class="group relative bg-white rounded-lg border border-gray-200 hover:shadow-lg transition-all duration-200 hover:-translate-y-1 overflow-hidden p-5 space-y-4">

    <div class="flex items-start justify-between gap-3">
        <div class="flex items-center gap-3 flex-1 min-w-0">
            <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-lg">
                ${iconForType(type)}
            </div>
            <div class="flex-1 min-w-0">
                <h3 class="truncate text-gray-900 font-semibold">${doc.name}</h3>
                <p class="text-gray-500 text-sm">${type.replace("_", " ")}</p>
            </div>
        </div>

        <div class="flex gap-1"> 
            <button onclick="openEditModal('${doc.id}')" ...>
            <img src="../static/icons/edit-box-line.svg" alt="Edit" class="w-5 h-5 text-gray-400 hover:text-gray-600">
            </button>
        </div>
    </div>

    ${riskBadge(doc)}

    <div class="space-y-3 text-sm mt-2">

        <div class="flex items-center gap-2">
            <span class="text-gray-600">Expires:</span>
            <span class="text-gray-900">${formatDate(doc.expiry_date)}</span>
        </div>

        ${doc.label ? `
        <div class="flex items-center gap-2">
            <span class="text-gray-600">Label:</span>
            <span class="bg-blue-50 border border-blue-200 text-blue-700 px-2 py-0.5 rounded-md text-xs">${doc.label}</span>
        </div>` : ""}

        ${doc.notes ? `
        <div class="pt-2 border-t border-gray-100">
            <p class="text-gray-600 text-xs">${doc.notes}</p>
        </div>` : ""}
    </div>
</div>`;
}


// =======================================================
//  RENDER LIST + FILTERING + STATS
// =======================================================
function renderDocumentList() {
    const listEl = document.getElementById("documentList");
    if (!listEl) return;

    const search = (document.getElementById("searchInput")?.value || "").toLowerCase();
    const typeFilter = document.getElementById("filterType")?.value || "all";
    const riskFilter = document.getElementById("filterImportance")?.value || "all";

    const filtered = allDocuments.filter((doc) => {
        const name = (doc.name || "").toLowerCase();
        const type = (doc.doc_type || "").toLowerCase();
        const label = (doc.label || "").toLowerCase();
        const matchText = name.includes(search) || type.includes(search) || label.includes(search);

        const typeOk = typeFilter === "all" || type === typeFilter;
        const riskOk = riskFilter === "all" || doc.risk === riskFilter;

        return matchText && typeOk && riskOk;
    });

    // Stats
    document.getElementById("statTotal").textContent = allDocuments.length;

    const actionNeeded = allDocuments.filter((d) => d.expiry_status === "IN_WINDOW").length;
    const criticalCount = allDocuments.filter((d) => d.risk === "CRITICAL").length;

    const boxExp = document.getElementById("statExpiringBox");
    const boxCrit = document.getElementById("statCriticalBox");

    document.getElementById("statExpiring").textContent = actionNeeded;
    document.getElementById("statCritical").textContent = criticalCount;
    boxExp.classList.toggle("hidden", actionNeeded === 0);
    boxCrit.classList.toggle("hidden", criticalCount === 0);

    // No results?
    if (filtered.length === 0) {
        listEl.innerHTML = `
            <div class="col-span-full text-center py-16">
                <div class="w-16 h-16 bg-white border border-gray-300 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span class="text-2xl text-gray-400">📄</span>
                </div>
                <h3 class="text-gray-900 mb-2">No documents found</h3>
                <p class="text-gray-600 text-sm">
                    ${search || typeFilter !== "all" || riskFilter !== "all"
                        ? "Try adjusting your search or filters."
                        : "Get started by adding your first document."}
                </p>
            </div>`;
        return;
    }

    listEl.innerHTML = filtered.map(renderCard).join("");
}


// =======================================================
//  LOAD DOCUMENTS (backend sorted)
// =======================================================
async function loadDocuments() {
    const res = await fetch("/api/documents?include_archived=true");
    const docs = await res.json();

    allDocuments = docs;
    console.log("Loaded documents:", docs);

    const activeList = document.getElementById("documentList");
    const archivedList = document.getElementById("archivedList");

    activeList.innerHTML = "";
    archivedList.innerHTML = "";

    docs.forEach(doc => {
        if (doc.archived === true) {
            archivedList.innerHTML += renderCard(doc);
        } else {
            activeList.innerHTML += renderCard(doc);
        }
    });

    // Update badge count on button
    const btn = document.getElementById("toggleArchiveBtn");
    if (btn) {
        const count = getArchivedCount();
        btn.textContent = showingArchived
            ? `Close Archived`
            : `Show Archived (${count})`;
    }

    updateStats(docs);
}

//======================================================
//  ARCHIVE DOCUMENT
// =======================================================

async function archiveCurrentDoc() {
    if (!currentEditDocId) return;

    const res = await fetch(`/api/documents/${currentEditDocId}/archive`, {
        method: "POST"
    });

    if (res.ok) {
        closeEditModal();
        loadDocuments();
    } else {
        alert("Failed to archive document");
    }
}
window.archiveCurrentDoc = archiveCurrentDoc;

//======================================================
//  UNARCHIVE DOCUMENT
// =======================================================
async function unarchiveCurrentDoc() {
    if (!currentEditDocId) return;

    const res = await fetch(`/api/documents/${currentEditDocId}/unarchive`, {
        method: "POST"
    });

    if (res.ok) {
        closeEditModal();
        loadDocuments();
    } else {
        alert("Failed to unarchive document");
    }
}
window.unarchiveCurrentDoc = unarchiveCurrentDoc;


// =======================================================
//  TOGGLE ARCHIVE VIEW
// =======================================================

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("archiveToggleBtn");
  const text = document.getElementById("archiveBtnText");
  const badge = document.getElementById("archiveBadge");

  function updateButtonUI(showingArchived) {

    // Variant switching (default vs outline)
    if (showingArchived) {
      btn.classList.remove("bg-white", "text-gray-700", "border-gray-300");
      btn.classList.add("bg-gray-700", "text-white", "hover:bg-gray-800");
      btn.textContent = `Close Archived`;
      badge.classList.add("hidden");
    } else {
      btn.classList.add("bg-white", "text-gray-700", "border-gray-300");
      btn.classList.remove("bg-gray-700", "text-white", "hover:bg-gray-800");
      btn.textContent = `Show Archived (${getArchivedCount()})`;

      if (getArchivedCount() > 0) {
        badge.classList.remove("hidden");
      }
    }
  }

  let showingArchived = false;
  updateButtonUI(showingArchived);

  btn.addEventListener("click", () => {
    showingArchived = !showingArchived;


    archivedSection.classList.toggle("hidden", !showingArchived);

    updateButtonUI(showingArchived);
  });
});




// =======================================================
//  DELETE DOCUMENT
// =======================================================
async function deleteCurrentDoc() {
    if (!currentEditDocId) return;

    const sure = confirm("Are you sure you want to delete this document?");
    if (!sure) return;

    const res = await fetch(`/api/documents/${currentEditDocId}`, {
        method: "DELETE"
    });

    if (res.ok) {
        closeEditModal();
        loadDocuments();
    } else {
        alert("Failed to delete document");
    }
}


// =======================================================
//  MODAL + FORM
// =======================================================
function openModal() {
    document.getElementById("docModal").classList.remove("hidden");
    document.getElementById("docModalBackdrop").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("docModal").classList.add("hidden");
    document.getElementById("docModalBackdrop").classList.add("hidden");
}

function openEditModal(id) {
    const doc = allDocuments.find(d => d.id === id);
    if (!doc) return;

    // Set current edit ID
    currentEditDocId = id;

    // Now modal is in DOM → populate fields
    setTimeout(() => {
        document.getElementById("edit_id").value = doc.id;
        document.getElementById("edit_name").value = doc.name || "";
        document.getElementById("edit_label").value = doc.label || "";
        document.getElementById("edit_expiry").value = doc.expiry_date || "";
        document.getElementById("edit_lead").value = doc.renewal_lead_time_days || "";
        document.getElementById("edit_importance").value = doc.importance || "";
        document.getElementById("edit_notes").value = doc.notes || "";

        // archive toggle
        const arch = document.getElementById("archiveBtn");
        const unarch = document.getElementById("unarchiveBtn");
        if (doc.archived) {
            arch.classList.add("hidden");
            unarch.classList.remove("hidden");
        } else {
            arch.classList.remove("hidden");
            unarch.classList.add("hidden");
        }
    }, 0);

    // Open modal
    document.getElementById("editModal").classList.remove("hidden");
    document.getElementById("docModalBackdrop").classList.remove("hidden");
}

function closeEditModal() {
    document.getElementById("editModal").classList.add("hidden");
    document.getElementById("docModalBackdrop").classList.add("hidden");
    currentEditDocId = null;
}



window.closeModal = closeModal;
window.openModal = openModal;
window.openEditModal = openEditModal;
window.closeEditModal = closeEditModal;


// =======================================================
//  AUTH LAYOUT CONTROL
// =======================================================
function enableAuthLayout() {
    const el = document.getElementById("bodyEl");
    el.classList.add("flex", "items-center", "justify-center");
}
function disableAuthLayout() {
    const el = document.getElementById("bodyEl");
    el.classList.remove("flex", "items-center", "justify-center");
}

function showDashboard() {
    disableAuthLayout();
    document.getElementById("authPanel").classList.add("hidden");
    document.getElementById("dashboard").classList.remove("hidden");
    loadDocuments();
}

function showAuth() {
    enableAuthLayout();
    document.getElementById("authPanel").classList.remove("hidden");
    document.getElementById("dashboard").classList.add("hidden");
}


// =======================================================
//  AUTH
// =======================================================
async function checkAuth() {
    const res = await fetch("/api/auth/me");
    const data = await res.json();
    if (data.logged_in) showDashboard();
    else showAuth();
}

async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    showAuth();
}
window.logout = logout;


// =======================================================
//  DOCUMENT CREATION
//  (name/importance/lead_time handled by backend)
// =======================================================
document.addEventListener("DOMContentLoaded", () => {

    // Login
    const loginForm = document.getElementById("loginForm");
    loginForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("loginEmail").value;
        const password = document.getElementById("loginPassword").value;

        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });

        if (res.ok) showDashboard();
        else alert("Login failed");
    });

    // Register
    const regForm = document.getElementById("registerForm");
    regForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("regEmail").value;
        const password = document.getElementById("regPassword").value;

        const res = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });

        if (res.ok) showDashboard();
        else alert("Registration failed");
    });

    // Create Document
    const addForm = document.getElementById("addForm");
    addForm?.addEventListener("submit", async (e) => {
        e.preventDefault();

        const payload = {
            doc_type: document.getElementById("doc_type").value,
            label: document.getElementById("label").value || null,
            expiry_date: document.getElementById("expiry_date").value,
            renewal_lead_time_days: document.getElementById("lead_time")?.value || null,
            importance: document.getElementById("importance")?.value || null,
            notes: document.getElementById("notes").value || null,
        };

        const res = await fetch("/api/documents", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (res.ok) {
            closeModal();
            addForm.reset();
            loadDocuments();
        } else {
            alert("Failed to add document");
        }
    });

    // Filters
    document.getElementById("searchInput")?.addEventListener("input", renderDocumentList);
   
    document.querySelectorAll("#filterType, #filterImportance").forEach(el => {
        el.addEventListener("change", renderDocumentList);
    });


    // Begin
    checkAuth();
});

// =======================================================
//  EDIT DOCUMENT
// =======================================================
document.getElementById("editForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const id = currentEditDocId;
    if (!id) return;

    const payload = {
        new_expiry_date: document.getElementById("edit_expiry").value,
        importance: document.getElementById("edit_importance").value,
        renewal_lead_time_days: document.getElementById("edit_lead").value
    };

    const res = await fetch(`/api/documents/${id}/renew`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        closeEditModal();
        loadDocuments();
    } else {
        alert("Failed to save.");
    }
});

// =======================================================
//  CALENDAR DOWNLOAD
// =======================================================
function downloadCalendar() {
    window.location.href = "/api/documents/calendar.ics";
}
window.downloadCalendar = downloadCalendar;


// =======================================================
//  TOGGLE ARCHIVE VIEW
// =======================================================
function toggleArchiveView() {
    const archivedSection = document.getElementById("archivedSection");
    const activeSection = document.getElementById("activeSection") || document.querySelector("main:not(#archivedSection)");
    const btn = document.getElementById("toggleArchiveBtn");

    showingArchived = !showingArchived;

    if (showingArchived) {
        archivedSection.classList.remove("hidden");
        activeSection.classList.add("hidden");
        btn.textContent = `Close Archived (${getArchivedCount()})`;
    } else {
        archivedSection.classList.add("hidden");
        activeSection.classList.remove("hidden");
        btn.textContent = `Show Archived (${getArchivedCount()})`;
    }
}

function getArchivedCount() {
    return allDocuments.filter(doc => doc.archived === true).length;
}

window.toggleArchiveView = toggleArchiveView;