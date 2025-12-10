// =======================================================
//  GLOBAL STATE
// =======================================================
let allDocuments = [];
let currentEditDocId = null;
let showingArchived = false;
let currentPage = 1;
let pageSize = 6;

function getLocalTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch (e) {
    return "UTC";
  }
}

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
    HIGH: "bg-orange-100 text-orange-700 border-orange-200",
    MEDIUM: "bg-yellow-100 text-yellow-700 border-yellow-200",
    LOW: "bg-green-100 text-green-700 border-green-200",
    UNKNOWN: "bg-gray-100 text-gray-700 border-gray-200",
  };

  const icons = {
    CRITICAL: "🔴",
    HIGH: "⚠️",
    MEDIUM: "🟡",
    LOW: "🟢",
    UNKNOWN: "❔",
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
  const icons = {
    passport: `
            <svg class="w-6 h-6"  fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
                 <path d="M20 2C20.5523 2 21 2.44772 21 3V21C21 21.5523 20.5523 22 20 22H4C3.44772 22 3 21.5523 3 21V3C3 2.44772 3.44772 2 4 2H20ZM19 4H5V20H19V4ZM16 16V18H8V16H16ZM12 6C14.2091 6 16 7.79086 16 10C16 12.2091 14.2091 14 12 14C9.79086 14 8 12.2091 8 10C8 7.79086 9.79086 6 12 6ZM12 8C10.8954 8 10 8.89543 10 10C10 11.1046 10.8954 12 12 12C13.1046 12 14 11.1046 14 10C14 8.89543 13.1046 8 12 8Z"></path>
            </svg>
        `,
    visa: `
            <svg class="w-6 h-6"  fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
                <path d="M3 18H21V6H3V18ZM1 5C1 4.44772 1.44772 4 2 4H22C22.5523 4 23 4.44772 23 5V19C23 19.5523 22.5523 20 22 20H2C1.44772 20 1 19.5523 1 19V5ZM9 10C9 9.44772 8.55228 9 8 9C7.44772 9 7 9.44772 7 10C7 10.5523 7.44772 11 8 11C8.55228 11 9 10.5523 9 10ZM11 10C11 11.6569 9.65685 13 8 13C6.34315 13 5 11.6569 5 10C5 8.34315 6.34315 7 8 7C9.65685 7 11 8.34315 11 10ZM8.0018 16C7.03503 16 6.1614 16.3907 5.52693 17.0251L4.11272 15.6109C5.10693 14.6167 6.4833 14 8.0018 14C9.52031 14 10.8967 14.6167 11.8909 15.6109L10.4767 17.0251C9.84221 16.3907 8.96858 16 8.0018 16ZM16.2071 14.7071L20.2071 10.7071L18.7929 9.29289L15.5 12.5858L13.7071 10.7929L12.2929 12.2071L14.7929 14.7071L15.5 15.4142L16.2071 14.7071Z"></path>
            </svg>
        `,
    driver_license: `
            <svg class="w-6 h-6"  fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
               <path d="M3 6H21V18H3V6ZM2 4C1.44772 4 1 4.44772 1 5V19C1 19.5523 1.44772 20 2 20H22C22.5523 20 23 19.5523 23 19V5C23 4.44772 22.5523 4 22 4H2ZM13 8H19V10H13V8ZM18 12H13V14H18V12ZM10.5 10C10.5 11.3807 9.38071 12.5 8 12.5C6.61929 12.5 5.5 11.3807 5.5 10C5.5 8.61929 6.61929 7.5 8 7.5C9.38071 7.5 10.5 8.61929 10.5 10ZM8 13.5C6.067 13.5 4.5 15.067 4.5 17H11.5C11.5 15.067 9.933 13.5 8 13.5Z"></path>
            </svg>
        `,
    permit: `
            <svg class="w-6 h-6"  fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
                <path d="M20 2C21.6569 2 23 3.34315 23 5V7H21V19C21 20.6569 19.6569 22 18 22H4C2.34315 22 1 20.6569 1 19V17H17V19C17 19.5128 17.386 19.9355 17.8834 19.9933L18 20C18.5128 20 18.9355 19.614 18.9933 19.1166L19 19V4H6C5.48716 4 5.06449 4.38604 5.00673 4.88338L5 5V15H3V5C3 3.34315 4.34315 2 6 2H20Z"></path>
            </svg>
        `,
    warranty: `
            <svg class="w-6 h-6"  fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
                 <path d="M10.0072 2.10365C8.60556 1.64993 7.08193 2.28104 6.41168 3.59294L5.6059 5.17011C5.51016 5.35751 5.35775 5.50992 5.17036 5.60566L3.59318 6.41144C2.28128 7.08169 1.65018 8.60532 2.10389 10.0069L2.64935 11.6919C2.71416 11.8921 2.71416 12.1077 2.64935 12.3079L2.10389 13.9929C1.65018 15.3945 2.28129 16.9181 3.59318 17.5883L5.17036 18.3941C5.35775 18.4899 5.51016 18.6423 5.6059 18.8297L6.41169 20.4068C7.08194 21.7187 8.60556 22.3498 10.0072 21.8961L11.6922 21.3507C11.8924 21.2859 12.1079 21.2859 12.3081 21.3507L13.9931 21.8961C15.3947 22.3498 16.9183 21.7187 17.5886 20.4068L18.3944 18.8297C18.4901 18.6423 18.6425 18.4899 18.8299 18.3941L20.4071 17.5883C21.719 16.9181 22.3501 15.3945 21.8964 13.9929L21.3509 12.3079C21.2861 12.1077 21.2861 11.8921 21.3509 11.6919L21.8964 10.0069C22.3501 8.60531 21.719 7.08169 20.4071 6.41144L18.8299 5.60566C18.6425 5.50992 18.4901 5.3575 18.3944 5.17011L17.5886 3.59294C16.9183 2.28104 15.3947 1.64993 13.9931 2.10365L12.3081 2.6491C12.1079 2.71391 11.8924 2.71391 11.6922 2.6491L10.0072 2.10365ZM8.19271 4.50286C8.41612 4.06556 8.924 3.8552 9.39119 4.00643L11.0762 4.55189C11.6768 4.74632 12.3235 4.74632 12.9241 4.55189L14.6091 4.00643C15.0763 3.8552 15.5841 4.06556 15.8076 4.50286L16.6133 6.08004C16.9006 6.64222 17.3578 7.09946 17.92 7.38668L19.4972 8.19246C19.9345 8.41588 20.1448 8.92375 19.9936 9.39095L19.4481 11.076C19.2537 11.6766 19.2537 12.3232 19.4481 12.9238L19.9936 14.6088C20.1448 15.076 19.9345 15.5839 19.4972 15.8073L17.92 16.6131C17.3578 16.9003 16.9006 17.3576 16.6133 17.9197L15.8076 19.4969C15.5841 19.9342 15.0763 20.1446 14.6091 19.9933L12.9241 19.4479C12.3235 19.2535 11.6768 19.2535 11.0762 19.4479L9.3912 19.9933C8.924 20.1446 8.41612 19.9342 8.19271 19.4969L7.38692 17.9197C7.09971 17.3576 6.64246 16.9003 6.08028 16.6131L4.50311 15.8073C4.06581 15.5839 3.85544 15.076 4.00668 14.6088L4.55213 12.9238C4.74656 12.3232 4.74656 11.6766 4.55213 11.076L4.00668 9.39095C3.85544 8.92375 4.06581 8.41588 4.50311 8.19246L6.08028 7.38668C6.64246 7.09946 7.09971 6.64222 7.38692 6.08004L8.19271 4.50286ZM6.75972 11.7573L11.0023 15.9999L18.0734 8.92885L16.6592 7.51464L11.0023 13.1715L8.17394 10.343L6.75972 11.7573Z"></path>
            </svg>
        `,
    insurance: `
            <svg class="w-6 h-6"  fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
               <path d="M5 4.60434V13.7889C5 15.1263 5.6684 16.3752 6.7812 17.1171L12 20.5963L17.2188 17.1171C18.3316 16.3752 19 15.1263 19 13.7889V4.60434L12 3.04879L5 4.60434ZM3.78307 2.82598L12 1L20.2169 2.82598C20.6745 2.92766 21 3.33347 21 3.80217V13.7889C21 15.795 19.9974 17.6684 18.3282 18.7812L12 23L5.6718 18.7812C4.00261 17.6684 3 15.795 3 13.7889V3.80217C3 3.33347 3.32553 2.92766 3.78307 2.82598ZM12 13.5L9.06107 15.0451L9.62236 11.7725L7.24472 9.45492L10.5305 8.97746L12 6L13.4695 8.97746L16.7553 9.45492L14.3776 11.7725L14.9389 15.0451L12 13.5Z"></path>
            </svg>
        `,
    membership: `
             <svg class="w-6 h-6"  fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
                 <path d="M2.00488 19H22.0049V21H2.00488V19ZM11.0049 8H13.0049V16H11.0049V8ZM7.97001 8L6.10912 13.1127L4.24824 8H2.12334L5.10912 15.9637H7.10912L10.0949 8H7.97001ZM17.0049 14V16H15.0049V8H19.0049C20.6617 8 22.0049 9.34315 22.0049 11C22.0049 12.6569 20.6617 14 19.0049 14H17.0049ZM17.0049 10V12H19.0049C19.5572 12 20.0049 11.5523 20.0049 11C20.0049 10.4477 19.5572 10 19.0049 10H17.0049ZM2.00488 3H22.0049V5H2.00488V3Z"></path>
            </svg>
        `,
    certification: `
             <svg class="w-6 h-6"  fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
               <path d="M12 6.99999C16.4183 6.99999 20 10.5817 20 15C20 19.4183 16.4183 23 12 23C7.58172 23 4 19.4183 4 15C4 10.5817 7.58172 6.99999 12 6.99999ZM12 8.99999C8.68629 8.99999 6 11.6863 6 15C6 18.3137 8.68629 21 12 21C15.3137 21 18 18.3137 18 15C18 11.6863 15.3137 8.99999 12 8.99999ZM12 10.5L13.3225 13.1797L16.2798 13.6094L14.1399 15.6953L14.645 18.6406L12 17.25L9.35497 18.6406L9.86012 15.6953L7.72025 13.6094L10.6775 13.1797L12 10.5ZM18 1.99999V4.99999L16.6366 6.13755C15.5305 5.5577 14.3025 5.17884 13.0011 5.04948L13 1.99899L18 1.99999ZM11 1.99899L10.9997 5.04939C9.6984 5.17863 8.47046 5.55735 7.36441 6.13703L6 4.99999V1.99999L11 1.99899Z"></path>
            </svg>`,
    subscription: `
             <svg class="w-6 h-6" fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
                <path d="M2.00488 19H22.0049V21H2.00488V19ZM2.00488 5L7.00488 8.5L12.0049 2L17.0049 8.5L22.0049 5V17H2.00488V5ZM4.00488 8.84131V15H20.0049V8.84131L16.5854 11.2349L12.0049 5.28024L7.42435 11.2349L4.00488 8.84131Z"></path>
            </svg>
        `,
    car_registration: `
            <svg class="w-6 h-6" fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
                <path d="M19 20H5V21C5 21.5523 4.55228 22 4 22H3C2.44772 22 2 21.5523 2 21V11L4.4805 5.21216C4.79566 4.47679 5.51874 4 6.31879 4H17.6812C18.4813 4 19.2043 4.47679 19.5195 5.21216L22 11V21C22 21.5523 21.5523 22 21 22H20C19.4477 22 19 21.5523 19 21V20ZM20 13H4V18H20V13ZM4.17594 11H19.8241L17.6812 6H6.31879L4.17594 11ZM6.5 17C5.67157 17 5 16.3284 5 15.5C5 14.6716 5.67157 14 6.5 14C7.32843 14 8 14.6716 8 15.5C8 16.3284 7.32843 17 6.5 17ZM17.5 17C16.6716 17 16 16.3284 16 15.5C16 14.6716 16.6716 14 17.5 14C18.3284 14 19 14.6716 19 15.5C19 16.3284 18.3284 17 17.5 17Z"></path>
            </svg>
        `,
    lease: `
           <svg class="w-6 h-6" fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
                <path d="M10.7577 11.8281L18.6066 3.97919L20.0208 5.3934L18.6066 6.80761L21.0815 9.28249L19.6673 10.6967L17.1924 8.22183L15.7782 9.63604L17.8995 11.7574L16.4853 13.1716L14.364 11.0503L12.1719 13.2423C13.4581 15.1837 13.246 17.8251 11.5355 19.5355C9.58291 21.4882 6.41709 21.4882 4.46447 19.5355C2.51184 17.5829 2.51184 14.4171 4.46447 12.4645C6.17493 10.754 8.81633 10.5419 10.7577 11.8281ZM10.1213 18.1213C11.2929 16.9497 11.2929 15.0503 10.1213 13.8787C8.94975 12.7071 7.05025 12.7071 5.87868 13.8787C4.70711 15.0503 4.70711 16.9497 5.87868 18.1213C7.05025 19.2929 8.94975 19.2929 10.1213 18.1213Z"></path>
            </svg>
        `,
    other: `
            <svg class="w-6 h-6" fill="currentColor" stroke-width="2"
                 viewBox="0 0 24 24">
                <path d="M4.5 10.5C3.675 10.5 3 11.175 3 12C3 12.825 3.675 13.5 4.5 13.5C5.325 13.5 6 12.825 6 12C6 11.175 5.325 10.5 4.5 10.5ZM19.5 10.5C18.675 10.5 18 11.175 18 12C18 12.825 18.675 13.5 19.5 13.5C20.325 13.5 21 12.825 21 12C21 11.175 20.325 10.5 19.5 10.5ZM12 10.5C11.175 10.5 10.5 11.175 10.5 12C10.5 12.825 11.175 13.5 12 13.5C12.825 13.5 13.5 12.825 13.5 12C13.5 11.175 12.825 10.5 12 10.5Z"></path>
            </svg>
        `,
  };

  return icons[type] || icons.other;
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".custom-select").forEach((select) => {
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
    menu.querySelectorAll(".dropdown-option").forEach((opt) => {
      opt.addEventListener("click", () => {
        const val = opt.dataset.value;
        const label = opt.textContent;

        hiddenInput.value = val;
        hiddenInput.dispatchEvent(new Event("change"));

        valueDisplay.textContent = label;
        valueDisplay.classList.remove("text-gray-500");

        menu.classList.remove("open");
        setTimeout(() => menu.classList.add("hidden"), 120);
      });
    });
  });

  // ---- CLICK OUTSIDE TO CLOSE ANY OPEN MENU ----
  document.addEventListener("click", (e) => {
    document.querySelectorAll(".custom-select").forEach((select) => {
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
  const expiring = docs.filter(
    (doc) => doc.last_risk === "HIGH" || doc.last_risk === "MEDIUM"
  ).length;
  const critical = docs.filter((doc) => doc.last_risk === "CRITICAL").length;

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
  // Handle YYYY-MM-DD specifically to avoid UTC/Timezone shifts
  if (typeof dateStr === "string" && dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
    const [y, m, d] = dateStr.split("-").map(Number);
    // new Date(y, mIndex, d) creates a Local Time date
    const date = new Date(y, m - 1, d);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  // Fallback
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
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
            <div class="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center">
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
            <path d="M9 1V3H15V1H17V3H21C21.5523 3 22 3.44772 22 4V20C22 20.5523 21.5523 21 21 21H3C2.44772 21 2 20.5523 2 20V4C2 3.44772 2.44772 3 3 3H7V1H9ZM20 11H4V19H20V11ZM7 5H4V9H20V5H17V7H15V5H9V7H7V5Z"></path>
            </svg>
            <span class="text-gray-600">Expires:</span>
            <span class="font-medium">${formatDate(doc.expiry_date)}</span>
        </div>

        <!-- Days Left -->
        ${doc.days_until !== undefined && doc.days_until !== null
      ? `
        <div class="flex items-center gap-2 text-gray-700">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22C6.47715 22 2 17.5228 2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12C22 17.5228 17.5228 22 12 22ZM12 20C16.4183 20 20 16.4183 20 12C20 7.58172 16.4183 4 12 4C7.58172 4 4 7.58172 4 12C4 16.4183 7.58172 20 12 20ZM13 12H17V14H11V7H13V12Z"></path>
        </svg>

        <span class="text-gray-600">Days Left:</span>
        <span class="font-medium">${doc.days_until} days</span>
        </div>
        `
      : ""
    }

        <!-- Label -->
        ${doc.label
      ? `
        <div class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.9042 2.10025L20.8037 3.51446L22.2179 13.414L13.0255 22.6063C12.635 22.9969 12.0019 22.9969 11.6113 22.6063L1.71184 12.7069C1.32131 12.3163 1.32131 11.6832 1.71184 11.2926L10.9042 2.10025ZM11.6113 4.22157L3.83316 11.9997L12.3184 20.485L20.0966 12.7069L19.036 5.28223L11.6113 4.22157ZM13.7327 10.5855C12.9516 9.80448 12.9516 8.53815 13.7327 7.7571C14.5137 6.97606 15.78 6.97606 16.5611 7.7571C17.3421 8.53815 17.3421 9.80448 16.5611 10.5855C15.78 11.3666 14.5137 11.3666 13.7327 10.5855Z"></path>
        </svg>

            <span class="text-gray-600">Label:</span>
            <span class="px-2 py-0.5 rounded-md bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium">
                ${doc.label}
            </span>
        </div>`
      : ""
    }

        <!-- Notes -->
        ${doc.notes
      ? `
        <div class="pt-2 border-t border-gray-100">
            <p class="text-gray-600 leading-relaxed text-sm">${doc.notes}</p>
        </div>`
      : ""
    }
    </div>

</div>`;
}

// =======================================================
// FILTER POPULATION
// =======================================================

function normalizeTypeName(type) {
  return (type || "other")
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function populateTypeFilter() {
  const wrapper = document.getElementById("filterTypeSelect");
  const dropdown = wrapper.querySelector(".dropdown-content");

  dropdown.innerHTML = `
        <div class="dropdown-option" data-value="all">All Types</div>
    `;

  const types = new Set(
    allDocuments.map((doc) => (doc.doc_type || "other").toLowerCase())
  );

  types.forEach((t) => {
    dropdown.innerHTML += `
            <div class="dropdown-option" data-value="${t}">
                ${normalizeTypeName(t)}
            </div>
        `;
  });

  // rebind click events because options were replaced dynamically
  dropdown.querySelectorAll(".dropdown-option").forEach((opt) => {
    opt.addEventListener("click", () => {
      const val = opt.dataset.value;
      wrapper.querySelector(".select-value").textContent =
        normalizeTypeName(val);
      document.getElementById("filterType").value = val;
      renderDocumentList();
      renderArchivedList();
    });
  });
}

function populateLabelFilter() {
  const select = document.getElementById("filterLabel");
  if (!select) return;

  const labels = new Set();
  (allDocuments || []).forEach((doc) => {
    if (doc.label && String(doc.label).trim()) {
      labels.add(String(doc.label).trim());
    }
  });

  // Keep first 2 options (All Labels, Unlabeled), then rebuild the rest
  select.innerHTML = `
    <option value="all">All Labels</option>
    <option value="__none__">Unlabeled</option>
  `;

  Array.from(labels)
    .sort((a, b) => a.localeCompare(b))
    .forEach((label) => {
      const opt = document.createElement("option");
      opt.value = label.toLowerCase();
      opt.textContent = label;
      select.appendChild(opt);
    });
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

  document.getElementById(
    "pageIndicator"
  ).textContent = `Page ${currentPage} of ${totalPages}`;

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
  pages.forEach((x) => {
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

  populateTypeFilter();
  populateLabelOptions();
  populateLabelFilter();
}

function renderDocumentList() {
  if (showingArchived) return;

  const listEl = document.getElementById("documentList");
  listEl.innerHTML = "";

  const searchValue = (document.getElementById("searchInput")?.value || "")
    .trim()
    .toLowerCase();
  const typeFilter = (
    document.getElementById("filterType")?.value || "all"
  ).toLowerCase();
  const riskFilter = (
    document.getElementById("filterImportance")?.value || "all"
  ).toUpperCase();
  const labelFilter = (
    document.getElementById("filterLabel")?.value || "all"
  ).toLowerCase();

  const allActiveDocs = allDocuments.filter(
    (d) => String(d.archived) !== "true"
  );

  const activeDocs = allActiveDocs.filter((doc) => {
    const name = (doc.name || "").toLowerCase();
    const label = (doc.label || "").toLowerCase();
    const notes = (doc.notes || "").toLowerCase();
    const type = (doc.doc_type || "other").toLowerCase();
    const risk = (doc.risk || "UNKNOWN").toUpperCase();

    const matchesSearch =
      !searchValue ||
      name.includes(searchValue) ||
      label.includes(searchValue) ||
      notes.includes(searchValue) ||
      type.includes(searchValue);

    const matchesType = typeFilter === "all" || type === typeFilter;

    const matchesRisk = riskFilter === "ALL" || risk === riskFilter;

    const docLabel = (doc.label || "").toLowerCase();

    const matchesLabel =
      labelFilter === "all" ||
      (labelFilter === "__none__" ? !docLabel : docLabel === labelFilter);

    return matchesSearch && matchesType && matchesRisk && matchesLabel;
  });

  const totalPages = Math.max(1, Math.ceil(activeDocs.length / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;

  const start = (currentPage - 1) * pageSize;
  const pageDocs = activeDocs.slice(start, start + pageSize);

  renderPaginationControls(totalPages);
  updatePagination(activeDocs.length);

  if (pageDocs.length === 0) {
    listEl.innerHTML = `<div class="px-4 py-2 text-gray-500">No documents found</div>`;
    return;
  }

  listEl.innerHTML = pageDocs.map(renderCard).join("");
}

function renderArchivedList() {
  if (!showingArchived) return;

  const listEl = document.getElementById("archivedList");
  listEl.innerHTML = "";

  const searchValue = (document.getElementById("searchInput")?.value || "")
    .trim()
    .toLowerCase();
  const typeFilter = (
    document.getElementById("filterType")?.value || "all"
  ).toLowerCase();
  const riskFilter = (
    document.getElementById("filterImportance")?.value || "all"
  ).toUpperCase();
  const labelFilter = (
    document.getElementById("filterLabel")?.value || "all"
  ).toLowerCase();

  const allArchivedDocs = allDocuments.filter(
    (d) => String(d.archived) === "true"
  );

  const archivedDocs = allArchivedDocs.filter((doc) => {
    const name = (doc.name || "").toLowerCase();
    const label = (doc.label || "").toLowerCase();
    const notes = (doc.notes || "").toLowerCase();
    const type = (doc.doc_type || "other").toLowerCase();
    const risk = (doc.risk || "UNKNOWN").toUpperCase();

    const matchesSearch =
      !searchValue ||
      name.includes(searchValue) ||
      label.includes(searchValue) ||
      notes.includes(searchValue) ||
      type.includes(searchValue);

    const matchesType = typeFilter === "all" || type === typeFilter;

    const matchesRisk = riskFilter === "ALL" || risk === riskFilter;

    const docLabel = (doc.label || "").toLowerCase();

    const matchesLabel =
      labelFilter === "all" ||
      (labelFilter === "__none__" ? !docLabel : docLabel === labelFilter);

    return matchesSearch && matchesType && matchesRisk && matchesLabel;
  });

  const totalPages = Math.max(1, Math.ceil(archivedDocs.length / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;

  const start = (currentPage - 1) * pageSize;
  const pageDocs = archivedDocs.slice(start, start + pageSize);

  renderPaginationControls(totalPages);
  updatePagination(archivedDocs.length);

  if (pageDocs.length === 0) {
    listEl.innerHTML = `<div class="px-4 py-2 text-gray-500">No archived documents</div>`;
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
    method: "POST",
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
    method: "POST",
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
  showingArchived = false;

  function getArchivedCount() {
    return allDocuments.filter((d) => d.archived === true).length;
  }

  function updateArchiveButton() {
    const count = getArchivedCount();

    if (showingArchived) {
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
    method: "DELETE",
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
  const doc = allDocuments.find((d) => d.id === id);
  if (!doc) return;

  currentEditDocId = id;

  // Now modal is in DOM → populate fields
  setTimeout(() => {
    document.getElementById("edit_id").value = doc.id;
    document.getElementById("edit_name").value = doc.name || "";
    document.getElementById("edit_label").value = doc.label || "";
    document.getElementById("edit_expiry").value = doc.expiry_date || "";
    document.getElementById("edit_lead").value =
      doc.renewal_lead_time_days || "";
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
//  INLINE AUTH MESSAGES (replaces alert/prompt)
// =======================================================
function showAuthMessage(which, text, kind = "info") {
  const id =
    which === "register"
      ? "registerMessage"
      : which === "forgot"
        ? "forgotMessage"
        : which === "reset"
          ? "resetMessage"
          : "loginMessage";
  const el = document.getElementById(id);
  if (!el) return;

  if (!text) {
    el.textContent = "";
    el.classList.add("hidden");
    return;
  }

  // reset style
  el.classList.remove(
    "bg-red-50", "border-red-200", "text-red-800",
    "bg-green-50", "border-green-200", "text-green-800",
    "bg-blue-50", "border-blue-200", "text-blue-800"
  );

  if (kind === "error") {
    el.classList.add("bg-red-50", "border-red-200", "text-red-800");
  } else if (kind === "success") {
    el.classList.add("bg-green-50", "border-green-200", "text-green-800");
  } else {
    el.classList.add("bg-blue-50", "border-blue-200", "text-blue-800");
  }

  el.textContent = text;
  el.classList.remove("hidden");
}

function clearAuthMessages() {
  showAuthMessage("login", "");
  showAuthMessage("register", "");
  showAuthMessage("forgot", "");
  showAuthMessage("reset", "");
}
window.clearAuthMessages = clearAuthMessages;

function showForgotPassword() {
  clearAuthMessages();
  document.getElementById("loginTabContent")?.classList.add("hidden");
  document.getElementById("registerTabContent")?.classList.add("hidden");
  document.getElementById("resetTabContent")?.classList.add("hidden");
  document.getElementById("forgotTabContent")?.classList.remove("hidden");
  // prefill from login email if present
  const loginEmail = document.getElementById("loginEmail")?.value || "";
  const forgotEmail = document.getElementById("forgotEmail");
  if (forgotEmail && !forgotEmail.value) forgotEmail.value = loginEmail;
}
window.showForgotPassword = showForgotPassword;

function showResetPasswordUI() {
  clearAuthMessages();
  document.getElementById("loginTabContent")?.classList.add("hidden");
  document.getElementById("registerTabContent")?.classList.add("hidden");
  document.getElementById("forgotTabContent")?.classList.add("hidden");
  document.getElementById("resetTabContent")?.classList.remove("hidden");
}

function showDashboard() {
  disableAuthLayout();
  clearAuthMessages();
  document.getElementById("authPanel").classList.add("hidden");
  document.getElementById("dashboard").classList.remove("hidden");
  loadDocuments();
}


// =======================================================
//  AUTH
// =======================================================
async function resendVerification() {
  // Use the login email field (no prompt pop-up)
  const email = (document.getElementById("loginEmail")?.value || "").trim();
  if (!email) {
    showAuthMessage("login", "Enter your email in the login form first, then click resend.", "error");
    return;
  }

  try {
    showAuthMessage("login", "Sending verification link...", "info");
    const res = await fetch("/api/auth/resend-verification", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const data = await res.json().catch(() => ({}));
    if (res.ok) showAuthMessage("login", data.message || "Done.", "success");
    else showAuthMessage("login", data.message || data.error || "Request failed.", "error");
  } catch (err) {
    showAuthMessage("login", "Failed to send request: " + err, "error");
  }
}
window.resendVerification = resendVerification;

async function checkAuth() {
  const res = await fetch("/api/auth/me");
  const data = await res.json();
  if (data.logged_in) {
    // Auto-Sync: If server timezone differs from browser, update it
    const localTz = getLocalTimezone();
    const serverTz = data.user.timezone || "UTC";

    if (localTz && serverTz !== localTz) {
      // silent update
      await fetch("/api/auth/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ timezone: localTz }),
      });
    }
    showDashboard();
  } else {
    showAuth();
  }
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
    clearAuthMessages();
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (res.ok) {
      checkAuth();
    } else {
      try {
        const data = await res.json().catch(() => ({}));
        if (res.status === 401) showAuthMessage("login", "Invalid email or password. Please double check!", "error");
        else if (res.status === 403 && data.error === "email_not_verified")
          showAuthMessage("login", "Email not verified. Click “Resend verification email”.", "error");
        else
          showAuthMessage("login", "Login failed: " + (data.error || "Unknown error"), "error");
      } catch (err) {
        showAuthMessage("login", "Login failed.", "error");
      }
    }
  });

  // Register
  const regForm = document.getElementById("registerForm");
  regForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAuthMessages();
    const email = document.getElementById("regEmail").value;
    const password = document.getElementById("regPassword").value;

    const timezone = getLocalTimezone();

    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, timezone }),
    });

    if (res.ok) {
      const data = await res.json();
      if (data.message) {
        showAuthMessage("register", data.message, "success");
        regForm.reset();
        return;
      }
      checkAuth();
    } else {
      try {
        const data = await res.json().catch(() => ({}));
        if (res.status === 409 || data.error === "email_already_registered") {
          showAuthMessage("register",
            "This email is already in use. Please login instead or use a different email.",
            "error"
          );
        } else {
          showAuthMessage("register", "Registration failed: " + (data.error || "Unknown error"), "error");
        }
      } catch (err) {
        showAuthMessage("register", "Registration failed: " + err, "error");
      }
    }
  });

  // Forgot password
  const forgotForm = document.getElementById("forgotForm");
  forgotForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAuthMessages();

    const email = (document.getElementById("forgotEmail")?.value || "").trim();
    if (!email) {
      showAuthMessage("forgot", "Please enter your email.", "error");
      return;
    }

    try {
      showAuthMessage("forgot", "Sending reset link...", "info");
      const res = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json().catch(() => ({}));
      // Always generic success message (secure, no enumeration)
      if (res.ok) {
        showAuthMessage(
          "forgot",
          data.message ||
          "If this account exists, a password reset link has been sent.",
          "success"
        );
      } else {
        showAuthMessage(
          "forgot",
          data.message || data.error || "Request failed.",
          "error"
        );
      }
    } catch (err) {
      showAuthMessage("forgot", "Failed to send request: " + err, "error");
    }
  });

  // Reset password
  const resetForm = document.getElementById("resetForm");
  resetForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAuthMessages();

    const params = new URLSearchParams(window.location.search);
    const token = params.get("reset_token");
    if (!token) {
      showAuthMessage("reset", "Missing reset token. Please use the link from your email.", "error");
      return;
    }

    const password = document.getElementById("resetPassword")?.value || "";
    const password2 = document.getElementById("resetPassword2")?.value || "";

    if (password.length < 8) {
      showAuthMessage("reset", "Password must be at least 8 characters.", "error");
      return;
    }
    if (password !== password2) {
      showAuthMessage("reset", "Passwords do not match.", "error");
      return;
    }

    try {
      showAuthMessage("reset", "Resetting password...", "info");
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password, password2 }),
      });

      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        // Remove token from URL for safety
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
        // Should be logged in now; go to dashboard
        checkAuth();
      } else {
        if (data.error === "invalid_or_expired_token") {
          showAuthMessage("reset", "Reset link is invalid or expired. Please request a new one.", "error");
        } else {
          showAuthMessage("reset", (data.error || "Reset failed."), "error");
        }
      }
    } catch (err) {
      showAuthMessage("reset", "Reset failed: " + err, "error");
    }
  });

  // Create Document
  const addForm = document.getElementById("addForm");
  addForm?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const docType = document.getElementById("doc_type").value;
    if (!docType) {
      alert("Please select a document type.");
      return;
    }

    const payload = {
      doc_type: docType,
      name: document.getElementById("name").value.trim() || null,
      label: document.getElementById("label").value || null,
      expiry_date: document.getElementById("expiry_date").value,
      renewal_lead_time_days:
        document.getElementById("lead_time")?.value || null,
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
  document.getElementById("searchInput")?.addEventListener("input", (e) => {
    renderDocumentList();
    renderArchivedList();
  });

  document.querySelectorAll("#filterType, #filterImportance, #filterLabel").forEach((el) => {
    el.addEventListener("change", (e) => {
      renderDocumentList();
      renderArchivedList();
    });
  });

  // Begin
  checkAuth();
});

// If the user opened a reset link, show reset UI immediately
document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  if (params.get("reset_token")) {
    showResetPasswordUI();
  }
});


// =======================================================
//  EDIT DOCUMENT
// =======================================================
document.getElementById("editForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const id = currentEditDocId;
  if (!id) return;

  const payload = {
    expiry_date: document.getElementById("edit_expiry").value,
    importance: document.getElementById("edit_importance").value,
    renewal_lead_time_days: document.getElementById("edit_lead").value,
    name: document.getElementById("edit_name").value,
    label: document.getElementById("edit_label").value,
    notes: document.getElementById("edit_notes").value,
  };

  const res = await fetch(`/api/documents/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    closeEditModal();
    loadDocuments();
  } else {
    alert("Failed to save.");
  }
});

function populateLabelOptions() {
  const dataList = document.getElementById("labelOptions");
  if (!dataList) return;

  dataList.innerHTML = "";

  // Get all unique labels from all non-archived documents
  const labels = new Set();
  if (allDocuments) {
    allDocuments.forEach((doc) => {
      if (doc.label) {
        labels.add(doc.label);
      }
    });
  }

  Array.from(labels)
    .sort()
    .forEach((label) => {
      const opt = document.createElement("option");
      opt.value = label;
      dataList.appendChild(opt);
    });
}

// =======================================================
//  CALENDAR DOWNLOAD
// =======================================================
function downloadCalendar() {
  window.location.href = "/api/documents/calendar.ics";
}
window.downloadCalendar = downloadCalendar;
