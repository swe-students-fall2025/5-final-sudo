// =======================================================
//  GLOBAL STATE
// =======================================================
let allDocuments = [];
let currentEditDocId = null;
let showingArchived = false;
let currentPage = 1;
let pageSize = 6;

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
<div class="group relative bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200 hover:-translate-y-1 p-6 space-y-5">

    <!-- TOP ROW: ICON + TITLE + EDIT -->
    <div class="flex items-start justify-between">
        
        <!-- Icon + Name -->
        <div class="flex items-start gap-4">
            <!-- Placeholder icon -->
            <div class="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center text-2xl">
                ${iconForType(type)}
            </div>

            <div>
                <h3 class="text-lg font-semibold text-gray-900">${doc.name}</h3>
                <p class="text-gray-500 text-sm">${type.replace("_", " ")}</p>
            </div>
        </div>

        <!-- Edit Button -->
        <button onclick="openEditModal('${doc.id}')" class="p-1 rounded-lg">
            <img src="../static/icons/edit-box-line.svg" class="w-5 h-5 text-gray-600 hover:text-gray-800">
        </button>
    </div>

    <!-- RISK BADGE -->
    ${riskBadge(doc)}

    <!-- DETAILS SECTION -->
    <div class="space-y-3 text-sm">

        <!-- Expiry -->
        <div class="flex items-center gap-2 text-gray-700">
             <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M7 3V1H9V3H15V1H17V3H21C21.5523 3 22 3.44772 22 4V9H20V5H17V7H15V5H9V7H7V5H4V19H10V21H3C2.44772 21 2 20.5523 2 20V4C2 3.44772 2.44772 3 3 3H7ZM17 12C14.7909 12 13 13.7909 13 16C13 18.2091 14.7909 20 17 20C19.2091 20 21 18.2091 21 16C21 13.7909 19.2091 12 17 12ZM11 16C11 12.6863 13.6863 10 17 10C20.3137 10 23 12.6863 23 16C23 19.3137 20.3137 22 17 22C13.6863 22 11 19.3137 11 16ZM16 13V16.4142L18.2929 18.7071L19.7071 17.2929L18 15.5858V13H16Z"></path>
            </svg>
            <span class="text-gray-600">Expires:</span>
            <span class="font-medium">${formatDate(doc.expiry_date)}</span>
        </div>

        <!-- Days Left -->
        ${doc.last_days_until !== undefined ? `
        <div class="flex items-center gap-2 text-gray-700">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
             <path d="M9 1V3H15V1H17V3H21C21.5523 3 22 3.44772 22 4V20C22 20.5523 21.5523 21 21 21H3C2.44772 21 2 20.5523 2 20V4C2 3.44772 2.44772 3 3 3H7V1H9ZM20 11H4V19H20V11ZM7 5H4V9H20V5H17V7H15V5H9V7H7V5Z"></path>
        </svg>

        <span class="text-gray-600">Days Left:</span>
        <span class="font-medium">${doc.last_days_until} days</span>
        </div>
        ` : "" }

        <!-- Label -->
        ${doc.label ? `
        <div class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.9042 2.10025L20.8037 3.51446L22.2179 13.414L13.0255 22.6063C12.635 22.9969 12.0019 22.9969 11.6113 22.6063L1.71184 12.7069C1.32131 12.3163 1.32131 11.6832 1.71184 11.2926L10.9042 2.10025ZM11.6113 4.22157L3.83316 11.9997L12.3184 20.485L20.0966 12.7069L19.036 5.28223L11.6113 4.22157ZM13.7327 10.5855C12.9516 9.80448 12.9516 8.53815 13.7327 7.7571C14.5137 6.97606 15.78 6.97606 16.5611 7.7571C17.3421 8.53815 17.3421 9.80448 16.5611 10.5855C15.78 11.3666 14.5137 11.3666 13.7327 10.5855Z"></path>
        </svg>

            <span class="text-gray-600">Label:</span>
            <span class="px-2 py-0.5 rounded-md bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium">
                ${doc.label}
            </span>
        </div>` : ""}

        <!-- Notes -->
        ${doc.notes ? `
        <div class="pt-2 border-t border-gray-100">
            <p class="text-gray-600 leading-relaxed text-sm">${doc.notes}</p>
        </div>` : ""}
    </div>

</div>`;
}


// =======================================================
//  PAGINATION RENDERING
// =======================================================
prevPageBtn.onclick = () => {
    if (currentPage > 1) {
        currentPage--;
        showingArchived ? renderArchivedList() : renderDocumentList();
    }
};

nextPageBtn.onclick = () => {
    currentPage++;
    showingArchived ? renderArchivedList() : renderDocumentList();
};

function updatePagination(totalItems) {
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

    document.getElementById("pageIndicator").textContent =
        `Page ${currentPage} of ${totalPages}`;

    // Disable prev/next appropriately
    document.getElementById("prevPageBtn").disabled = currentPage <= 1;
    document.getElementById("nextPageBtn").disabled = currentPage >= totalPages;
}

function renderPaginationControls(totalPages) {
    const container = document.getElementById("paginationNumbers");
    if (!container) return;

    container.innerHTML = "";

    // Helper to create a number button
    function pageBtn(page) {
        const el = document.createElement("button");
        el.textContent = page;
        el.className =
            "px-2 py-1 rounded text-sm " +
            (page === currentPage
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100");

        el.onclick = () => {
            currentPage = page;
            renderDocumentList();
        };
        return el;
    }

    // Logic for collapsing long page lists
    const pages = [];

    if (totalPages <= 7) {
        // show all pages
        for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
        // Always show first 2
        pages.push(1, 2);

        if (currentPage > 4) pages.push("…");

        // Middle block
        const start = Math.max(3, currentPage - 1);
        const end = Math.min(totalPages - 2, currentPage + 1);
        for (let i = start; i <= end; i++) pages.push(i);

        if (currentPage < totalPages - 3) pages.push("…");

        // Always show last 2
        pages.push(totalPages - 1, totalPages);
    }

    // Render buttons
    pages.forEach(x => {
        if (x === "…") {
            const dot = document.createElement("span");
            dot.textContent = "…";
            dot.className = "px-2 text-gray-500";
            container.appendChild(dot);
        } else {
            container.appendChild(pageBtn(x));
        }
    });

    // Update prev/next state
    document.getElementById("prevPageBtn").disabled = currentPage === 1;
    document.getElementById("nextPageBtn").disabled = currentPage === totalPages;
}

// =======================================================
//  RENDER LIST + FILTERING + STATS
// =======================================================
function renderDocumentList() {
    const listEl = document.getElementById("documentList");
    if (!listEl) return;

    // --- Get filter values ONCE ---
    const searchValue = (document.getElementById("searchInput")?.value || "").trim().toLowerCase();
    const typeFilter = (document.getElementById("filterType")?.value || "all").toLowerCase();
    const riskFilter = (document.getElementById("filterImportance")?.value || "all").toUpperCase();

    // --- Filter documents efficiently ---
    const filtered = allDocuments.filter(doc => {
        // Normalize values once
        const name = (doc.name || "").toLowerCase();
        const type = (doc.doc_type || "").toLowerCase();
        const label = (doc.label || "").toLowerCase();
        const risk = (doc.risk || "").toUpperCase();

        // Text search (name, type, label)
        const matchesText =
            !searchValue ||
            name.includes(searchValue) ||
            type.includes(searchValue) ||
            label.includes(searchValue);

        // Type filter
        const matchesType = typeFilter === "all" || type === typeFilter;

        // Risk filter
        const matchesRisk = riskFilter === "all" || risk === riskFilter;

        return matchesText && matchesType && matchesRisk;

        
    });

    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));

    // Reset page if filters changed or page out of range
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const start = (currentPage - 1) * pageSize;
    const pageDocs = filtered.slice(start, start + pageSize);

    // --- Update stats ---
    const totalDocs = allDocuments.length;
    const actionNeeded = allDocuments.filter(d => d.expiry_status === "IN_WINDOW").length;
    const criticalCount = allDocuments.filter(d => d.risk === "CRITICAL").length;

    document.getElementById("statTotal").textContent = totalDocs;
    document.getElementById("statExpiring").textContent = actionNeeded;
    document.getElementById("statCritical").textContent = criticalCount;

    document.getElementById("statExpiringBox").classList.toggle("hidden", actionNeeded === 0);
    document.getElementById("statCriticalBox").classList.toggle("hidden", criticalCount === 0);

    // --- Render "No results" state ---
    if (pageDocs.length === 0) {
        const isFiltering = !!searchValue || typeFilter !== "all" || riskFilter !== "all";

        listEl.innerHTML = `
            <div class="col-span-full text-center py-16">
                <div class="w-16 h-16 bg-white border border-gray-300 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span class="text-2xl text-gray-400">📄</span>
                </div>
                <h3 class="text-gray-900 mb-2">No documents found</h3>
                <p class="text-gray-600 text-sm">
                    ${isFiltering
                        ? "Try adjusting your search or filters."
                        : "Get started by adding your first document."}
                </p>
            </div>`;
        return;
    }

    // --- Render results ---
    listEl.innerHTML = filtered.map(renderCard).join("");
}

// =======================================================
//  LOAD DOCUMENTS (backend sorted)
// =======================================================

async function loadDocuments() {
    const res = await fetch("/api/documents?include_archived=true");
    allDocuments = await res.json();

    updateStats(allDocuments);
     requestAnimationFrame(() => refreshArchiveButton());

    // Re-render depending on current mode
    if (showingArchived) renderArchivedList();
    else renderDocumentList();
}

function renderDocumentList() {
    if (showingArchived) return;  // don’t render if wrong mode

    const listEl = document.getElementById("documentList");
    listEl.innerHTML = "";

    const search = (document.getElementById("searchInput")?.value || "").toLowerCase();
    const typeFilter = document.getElementById("filterType")?.value || "all";
    const riskFilter = (document.getElementById("filterImportance")?.value || "all").toUpperCase();

    const activeDocs = allDocuments.filter(d => String(d.archived) !== "true");

    // filtering
    // const filtered = activeDocs.filter(doc => {
    //     const name = (doc.name || "").toLowerCase();
    //     const type = (doc.doc_type || "").toLowerCase();
    //     const label = (doc.label || "").toLowerCase();
    //     const risk = (doc.risk || "").toUpperCase();

    //     const matchesText = name.includes(search) || type.includes(search) || label.includes(search);
    //     const matchesType = typeFilter === "all" || type === typeFilter;
    //     const matchesRisk = riskFilter === "all" || risk === riskFilter;

    //     return matchesText && matchesType && matchesRisk;
    // });

    // pagination
    const totalPages = Math.max(1, Math.ceil(activeDocs.length / pageSize));
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * pageSize;
    const pageDocs = activeDocs.slice(start, start + pageSize);
    

    renderPaginationControls(totalPages);
    updatePagination(activeDocs.length);


    if (pageDocs.length === 0) {
        listEl.innerHTML = `<div class="py-12 text-center text-gray-500">No documents found</div>`;
        return;
    }

    listEl.innerHTML = pageDocs.map(renderCard).join("");
    
}


function renderArchivedList() {
    if (!showingArchived) return; // only render in archived mode

    const listEl = document.getElementById("archivedList");
    listEl.innerHTML = "";

    const archivedDocs = allDocuments.filter(d => String(d.archived) === "true");

    const totalPages = Math.max(1, Math.ceil(archivedDocs.length / pageSize));
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * pageSize;
    const pageDocs = archivedDocs.slice(start, start + pageSize);

    renderPaginationControls(totalPages);
    updatePagination(archivedDocs.length);

    if (pageDocs.length === 0) {
        listEl.innerHTML = `<div class="py-12 text-center text-gray-500">No archived documents</div>`;
        return;
    }

    listEl.innerHTML = pageDocs.map(renderCard).join("");
}


function updateArchiveCount() {
    // Update badge count on button
    const btn = document.getElementById("toggleArchiveBtn");
    if (btn) {
        const count = getArchivedCount();
        btn.textContent = showingArchived
            ? `Close Archived`
            : `Show Archived (${count})`;
    }
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
    const badge = document.getElementById("archiveBadge");

    const archivedSection = document.getElementById("archivedSection");
    const activeSection = document.getElementById("documentList").closest("main");

    // Global state
    window.showingArchived = false;

    function getArchivedCount() {
        return allDocuments.filter(d => d.archived === true).length;
    }

    function updateArchiveButton() {
        const count = getArchivedCount();

        if (window.showingArchived) {
            // --- Archived view active ---
            btn.textContent = "Close Archived";
            btn.classList.remove("bg-white", "text-gray-700", "border-gray-300");
            btn.classList.add("bg-gray-700", "text-white", "hover:bg-gray-800");
            badge.classList.add("hidden");
        } else {
            // --- Active view ---
            btn.textContent = `Show Archived (${count})`;
            btn.classList.add("bg-white", "text-gray-700", "border-gray-300");
            btn.classList.remove("bg-gray-700", "text-white", "hover:bg-gray-800");

            if (count > 0) badge.classList.remove("hidden");
            else badge.classList.add("hidden");
        }
    }

    // Toggle logic
    btn.addEventListener("click", () => {
    showingArchived = !showingArchived;
    currentPage = 1;

    if (showingArchived) {
        document.getElementById("documentSection").classList.add("hidden");
        document.getElementById("archivedSection").classList.remove("hidden");
        renderArchivedList();
    } else {
        document.getElementById("archivedSection").classList.add("hidden");
        document.getElementById("documentSection").classList.remove("hidden");
        renderDocumentList();
    }

    refreshArchiveButton();
    });


    // Called **after loadDocuments()** resets content
    window.refreshArchiveButton = function () {
        updateArchiveButton();
    };
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
window.deleteCurrentDoc = deleteCurrentDoc;


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

    currentEditDocId = id;

    // Now modal is in DOM → populate fields
    setTimeout(() => {
        document.getElementById("edit_id").value = doc.id;
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
