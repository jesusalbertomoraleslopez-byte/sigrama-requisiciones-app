/**
 * CONTROLADOR KANBAN STREAMLIT - ODOO CRM
 * Arrastre y Soltar (Drag & Drop a 60 FPS) mediante SortableJS con comunicación bidireccional
 */

let sortableInstances = [];
let currentColumns = [];

// ==========================================================================
// 1. PROTOCOLO BIDIRECCIONAL STREAMLIT COMPONENT
// ==========================================================================
function sendValueToStreamlit(value) {
    window.parent.postMessage({
        isStreamlitMessage: true,
        type: "streamlit:setComponentValue",
        value: value
    }, "*");
}

function sendFrameHeight(height) {
    window.parent.postMessage({
        isStreamlitMessage: true,
        type: "streamlit:setFrameHeight",
        height: height || 740
    }, "*");
}

function notifyComponentReady() {
    window.parent.postMessage({
        isStreamlitMessage: true,
        type: "streamlit:componentReady",
        apiVersion: 1
    }, "*");
}

// Escuchar evento de renderizado enviado por Python desde Streamlit
window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "streamlit:render") {
        const { args } = event.data;
        if (args && args.columns) {
            currentColumns = args.columns;
            renderKanbanBoard(args.columns, args.total_count || 0);
            sendFrameHeight(740);
        }
    }
});

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
    notifyComponentReady();
    sendFrameHeight(740);
});

// ==========================================================================
// 2. RENDERIZADO DEL TABLERO KANBAN CON SORTABLEJS
// ==========================================================================
function renderKanbanBoard(columns, totalCount) {
    const boardContainer = document.getElementById("kanbanBoard");
    if (!boardContainer) return;

    // Destruir instancias previas
    sortableInstances.forEach(inst => inst.destroy());
    sortableInstances = [];
    boardContainer.innerHTML = "";

    columns.forEach(col => {
        const columnEl = document.createElement("div");
        columnEl.className = "kanban-column";
        columnEl.dataset.stageId = col.id;

        const formattedTotal = new Intl.NumberFormat('es-MX', {
            style: 'currency',
            currency: 'MXN',
            maximumFractionDigits: 0
        }).format(col.total_monto || 0);

        columnEl.innerHTML = `
            <div class="column-header">
                <div class="column-top-bar" style="background-color: ${col.color};"></div>
                <div class="column-title-row">
                    <span class="column-title" style="color: ${col.accent};">
                        <span>${col.icon}</span> ${col.short_title}
                    </span>
                    <span class="column-badge" id="badge-${col.id}">${col.cards.length}</span>
                </div>
                <div class="column-metrics-row">
                    <span style="font-size: 11px; color: #64748B;">Subtotal:</span>
                    <span class="column-total">${formattedTotal}</span>
                </div>
                <div class="column-progress-bar">
                    <div class="column-progress-fill" style="width: ${Math.min(100, (col.cards.length / Math.max(1, totalCount)) * 260)}%; background-color: ${col.color};"></div>
                </div>
            </div>
            <div class="kanban-cards-dropzone" id="dropzone-${col.id}" data-stage-id="${col.id}" data-db-status="${col.db_status}"></div>
        `;

        const dropzoneEl = columnEl.querySelector(".kanban-cards-dropzone");

        col.cards.forEach(card => {
            const cardEl = createCardElement(card);
            dropzoneEl.appendChild(cardEl);
        });

        boardContainer.appendChild(columnEl);

        // ==================================================================
        // SORTABLE JS - ARRASTRE FLUIDO A 60 FPS
        // ==================================================================
        const sortable = new Sortable(dropzoneEl, {
            group: "odoo_kanban_group",
            animation: 180,
            ghostClass: "sortable-ghost",
            chosenClass: "sortable-chosen",
            dragClass: "sortable-drag",
            fallbackTolerance: 3,
            scroll: true,
            scrollSensitivity: 80,
            scrollSpeed: 15,
            bubbleScroll: true,

            onEnd: function (evt) {
                const itemEl = evt.item;
                const fromColId = evt.from.dataset.stageId;
                const toColId = evt.to.dataset.stageId;
                const reqId = itemEl.dataset.reqId;
                const newDbStatus = evt.to.dataset.dbStatus;

                // Si la tarjeta cambió de columna
                if (fromColId !== toColId) {
                    // Notificar inmediatamente a Python (Streamlit)
                    sendValueToStreamlit({
                        action: "move_stage",
                        req_id: reqId,
                        old_stage: fromColId,
                        new_stage: toColId,
                        new_db_status: newDbStatus
                    });
                }
            }
        });

        sortableInstances.push(sortable);
    });
}

// ==========================================================================
// 3. TARJETAS POST-IT
// ==========================================================================
function createCardElement(card) {
    const cardEl = document.createElement("div");
    cardEl.className = "postit-card";
    cardEl.dataset.reqId = card.id;

    cardEl.style.backgroundColor = card.bg_color || "#FEF08A";
    cardEl.style.borderColor = card.border_color || "#FDE047";
    cardEl.style.borderTopColor = card.top_color || "#CA8A04";

    const formattedMonto = new Intl.NumberFormat('es-MX', {
        style: 'currency',
        currency: card.moneda || 'MXN'
    }).format(card.monto || 0);

    const poTag = card.folio_po 
        ? `<span class="card-po-badge">📝 ${card.folio_po}</span>` 
        : "";

    const solTag = card.folio_solicitud 
        ? `<span class="card-sol-tag">${card.folio_solicitud}</span>` 
        : "";

    const priorityStars = card.prioridad === "Urgente" || card.prioridad === "Alta" 
        ? "⭐⭐⭐" 
        : (card.prioridad === "Media" ? "⭐⭐☆" : "⭐☆☆");

    cardEl.innerHTML = `
        <div>
            <div class="card-header">
                <span class="card-folio">📌 ${card.id}</span>
                ${solTag}
            </div>
            <div class="card-title">${escapeHtml(card.descripcion || "Sin descripción")}</div>
        </div>
        <div>
            <div class="card-amount-row">
                <span class="card-amount">💰 ${formattedMonto}</span>
                ${poTag}
            </div>
            <div class="card-user-row">
                <span style="background-color:${card.avatar_bg || '#6366F1'}; color:#FFFFFF; width:18px; height:18px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:9px; font-weight:800;">
                    ${card.initials || 'SG'}
                </span>
                <span><strong>${escapeHtml(card.solicitante || 'Sin asignar')}</strong> ${card.area ? `&bull; 📍 ${escapeHtml(card.area)}` : ''}</span>
            </div>
            <div class="card-footer-meta">
                <span>${priorityStars} ${card.prioridad}</span>
                <span style="font-weight:700;">📑 ${card.num_cotizaciones || 0} cotiz.</span>
            </div>
            <button class="card-open-btn" onclick="openExpedienteModal('${card.id}')">
                👁️ Abrir Expediente
            </button>
        </div>
    `;

    // Doble clic abre el expediente
    cardEl.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        openExpedienteModal(card.id);
    });

    return cardEl;
}

function openExpedienteModal(reqId) {
    // Notificar a Streamlit para abrir la modal nativa @st.dialog
    sendValueToStreamlit({
        action: "open_modal",
        req_id: reqId
    });
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}
