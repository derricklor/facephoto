const peopleList = document.getElementById('people-list');
const photoGrid = document.getElementById('photo-grid');
const scanBtn = document.getElementById('scan-btn');
const browseBtn = document.getElementById('browse-btn');
const dirInput = document.getElementById('dir-input');
const galleryTitle = document.getElementById('gallery-title');

const controlPanel = document.getElementById('control-panel');
const openRenameBtn = document.getElementById('open-rename-btn');
const exportPersonBtn = document.getElementById('export-person-btn');
const deletePersonBtn = document.getElementById('delete-person-btn');

const renameModal = document.getElementById('rename-modal');
const renameInput = document.getElementById('rename-input');
const cancelRenameBtn = document.getElementById('cancel-rename-btn');
const confirmRenameBtn = document.getElementById('confirm-rename-btn');

const openMergeBtn = document.getElementById('open-merge-btn');
const moveModal = document.getElementById('move-modal');
const movePeopleList = document.getElementById('move-people-list');
const cancelMoveBtn = document.getElementById('cancel-move-btn');
const confirmMoveBtn = document.getElementById('confirm-move-btn');
const moveModalTitle = document.getElementById('move-modal-title');
const moveModalDesc = document.getElementById('move-modal-desc');

const bulkActions = document.getElementById('bulk-actions');
const selectionCount = document.getElementById('selection-count');
const bulkMoveBtn = document.getElementById('bulk-move-btn');
const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
const clearSelectionBtn = document.getElementById('clear-selection-btn');

const zoomOverlay = document.getElementById('zoom-overlay');
const zoomImg = document.getElementById('zoom-img');
const closeZoom = document.getElementById('close-zoom');

const darkModeToggle = document.getElementById('dark-mode-toggle');
const sunIcon = document.getElementById('sun-icon');
const moonIcon = document.getElementById('moon-icon');

const infoModal = document.getElementById('info-modal');
const infoModalTitle = document.getElementById('info-modal-title');
const infoModalMessage = document.getElementById('info-modal-message');
const infoModalList = document.getElementById('info-modal-list');
const infoOkBtn = document.getElementById('info-ok-btn');
const infoCancelBtn = document.getElementById('info-cancel-btn');

const scanProgressContainer = document.getElementById('scan-progress-container');
const scanStatusText = document.getElementById('scan-status-text');
const scanPercentage = document.getElementById('scan-percentage');
const scanProgressBar = document.getElementById('scan-progress-bar');

const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const closeSettingsBtn = document.getElementById('close-settings-btn');
const settingsOkBtn = document.getElementById('settings-ok-btn');
const clearCacheBtn = document.getElementById('clear-cache-btn');

let selectedGroup = null;
let moveTargetGroup = null;
let allGroups = [];
let selectedPhotoIds = [];
let isBulkMode = false;

// Custom Alert/Confirm Logic
function showInfo(title, message, isConfirm = false, listItems = []) {
    return new Promise((resolve) => {
        infoModalTitle.innerText = title;
        infoModalMessage.innerText = message;
        infoModalList.innerHTML = '';

        if (listItems && listItems.length > 0) {
            infoModalList.classList.remove('hidden');
            listItems.forEach(item => {
                const div = document.createElement('div');
                div.className = 'p-2 bg-gray-50 dark:bg-slate-700 rounded text-xs border dark:border-slate-600';
                if (typeof item === 'string') {
                    div.innerText = item;
                } else {
                    div.innerHTML = `<span class="font-bold text-red-500">${item.file}:</span> ${item.error}`;
                }
                infoModalList.appendChild(div);
            });
        } else {
            infoModalList.classList.add('hidden');
        }

        if (isConfirm) {
            infoCancelBtn.classList.remove('hidden');
        } else {
            infoCancelBtn.classList.add('hidden');
        }

        infoModal.classList.remove('hidden');

        const handleOk = () => {
            infoModal.classList.add('hidden');
            cleanup();
            resolve(true);
        };

        const handleCancel = () => {
            infoModal.classList.add('hidden');
            cleanup();
            resolve(false);
        };

        const cleanup = () => {
            infoOkBtn.removeEventListener('click', handleOk);
            infoCancelBtn.removeEventListener('click', handleCancel);
        };

        infoOkBtn.addEventListener('click', handleOk);
        infoCancelBtn.addEventListener('click', handleCancel);
    });
}

// Dark Mode Logic
if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
    sunIcon.classList.remove('hidden');
    moonIcon.classList.add('hidden');
}

darkModeToggle.onclick = () => {
    if (document.documentElement.classList.contains('dark')) {
        document.documentElement.classList.remove('dark');
        localStorage.theme = 'light';
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
    } else {
        document.documentElement.classList.add('dark');
        localStorage.theme = 'dark';
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
    }
};

async function fetchGroups() {
    const res = await fetch('/api/groups');
    allGroups = await res.json();
    renderPeople(allGroups);

    if (selectedGroup) {
        const updated = allGroups.find(g => g.id === selectedGroup.id);
        if (updated) {
            selectPerson(updated);
        } else {
            selectedGroup = null;
            controlPanel.classList.add('hidden');
            photoGrid.innerHTML = '';
            galleryTitle.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-blue-500 inline mr-2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                        </svg>
                        All Photos
                    `;
        }
    }
}

function renderPeople(groups) {
    peopleList.innerHTML = '';
    if (groups.length === 0) {
        peopleList.innerHTML = '<p class="text-gray-500 italic dark:text-slate-400">No people identified yet.</p>';
        return;
    }

    groups.forEach(group => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-3 p-3 bg-white dark:bg-slate-800 rounded-lg shadow cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-700 transition person-item';
        div.dataset.id = group.id;
        if (selectedGroup && selectedGroup.id === group.id) {
            div.classList.add('selected-person');
        }

        div.onclick = () => selectPerson(group);

        div.innerHTML = `
                    <img src="/api/image?path=${encodeURIComponent(group.thumbnail)}" class="w-12 h-12 rounded-full object-cover bg-gray-200 dark:bg-slate-700">
                    <div>
                        <p class="font-semibold dark:text-slate-200">${group.name}</p>
                        <p class="text-sm text-gray-500 dark:text-slate-400">${group.photo_count} photos</p>
                    </div>
                `;
        peopleList.appendChild(div);
    });
}

function selectPerson(group) {
    selectedGroup = group;
    clearSelection();

    document.querySelectorAll('.person-item').forEach(el => {
        el.classList.toggle('selected-person', parseInt(el.dataset.id) === group.id);
    });

    controlPanel.classList.remove('hidden');
    renderPhotos(group);
}

function renderPhotos(group) {
    galleryTitle.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-blue-500 inline mr-2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
                Photos of ${group.name}
            `;
    photoGrid.innerHTML = '';
    group.photos.forEach(photo => {
        const card = document.createElement('div');
        card.className = 'photo-card group';

        const imgSrc = `/api/image?path=${encodeURIComponent(photo.path)}`;
        const img = document.createElement('img');
        img.src = imgSrc;
        img.className = 'w-full h-48 object-cover rounded shadow-md hover:opacity-90 transition cursor-zoom-in';
        img.onclick = (e) => {
            e.stopPropagation();
            openZoom(imgSrc);
        };

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'photo-checkbox opacity-0 group-hover:opacity-100 checked:opacity-100 transition-opacity duration-200';
        checkbox.onclick = (e) => e.stopPropagation();
        checkbox.onchange = (e) => {
            if (e.target.checked) {
                selectedPhotoIds.push(photo.id);
            } else {
                selectedPhotoIds = selectedPhotoIds.filter(id => id !== photo.id);
            }
            updateBulkUI();
        };

        card.appendChild(img);
        card.appendChild(checkbox);
        photoGrid.appendChild(card);
    });
}

function updateBulkUI() {
    if (selectedPhotoIds.length > 0) {
        bulkActions.classList.remove('hidden');
        selectionCount.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    ${selectedPhotoIds.length} selected
                `;
    } else {
        bulkActions.classList.add('hidden');
    }
}

function clearSelection() {
    selectedPhotoIds = [];
    document.querySelectorAll('.photo-checkbox').forEach(cb => cb.checked = false);
    updateBulkUI();
}

clearSelectionBtn.onclick = clearSelection;

function openZoom(src) {
    zoomImg.src = src;
    zoomOverlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeZoomOverlay() {
    zoomOverlay.style.display = 'none';
    zoomImg.src = '';
    document.body.style.overflow = 'auto';
}

zoomOverlay.onclick = closeZoomOverlay;
closeZoom.onclick = (e) => { e.stopPropagation(); closeZoomOverlay(); };

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeZoomOverlay(); });

browseBtn.onclick = async () => {
    const res = await fetch('/api/browse');
    const data = await res.json();
    if (data.path) {
        dirInput.value = data.path;
    }
};

async function pollScanProgress() {
    const res = await fetch('/api/scan/progress');
    const data = await res.json();

    if (data.is_active || data.status === 'Completed' || data.status.startsWith('Error')) {
        scanProgressContainer.classList.remove('hidden');
        
        // Calculate percentage
        const percent = data.total > 0 ? Math.round((data.current / data.total) * 100) : 0;
        
        // Update UI
        scanStatusText.innerText = data.status;
        scanPercentage.innerText = `${percent}%`;
        scanProgressBar.style.width = `${percent}%`;

        if (data.is_active) {
            // Continue polling
            setTimeout(pollScanProgress, 1000);
        } else {
            // Finished or Error
            if (data.status === 'Completed') {
                const errorCount = data.errors ? data.errors.length : 0;
                let message = 'Directory scan and face clustering finished successfully.';
                if (errorCount > 0) {
                    message += ` However, ${errorCount} errors occurred during processing.`;
                }
                await showInfo('Scan Complete', message, false, data.errors || []);
                await fetchGroups();
            } else if (data.status.startsWith('Error')) {
                await showInfo('Scan Error', data.status);
            }
            
            // Hide progress after a delay
            setTimeout(() => {
                scanProgressContainer.classList.add('hidden');
                // Reset for next time
                scanProgressBar.style.width = '0%';
                scanPercentage.innerText = '0%';
            }, 3000);
        }
    } else {
        scanProgressContainer.classList.add('hidden');
    }
}

scanBtn.onclick = async () => {
    const dir = dirInput.value;
    if (!dir) {
        await showInfo('Directory Required', 'Please enter a directory path');
        return;
    }
    const res = await fetch('/api/scan?directory=' + encodeURIComponent(dir), { method: 'POST' });
    if (res.ok) {
        pollScanProgress();
    } else {
        const error = await res.json();
        await showInfo('Scan Failed', error.detail || 'Failed to start scan');
    }
};

// Rename logic
openRenameBtn.onclick = () => {
    if (!selectedGroup) return;
    renameInput.value = selectedGroup.name;
    renameModal.classList.remove('hidden');
    renameInput.focus();
};

cancelRenameBtn.onclick = () => renameModal.classList.add('hidden');

confirmRenameBtn.onclick = async () => {
    const newName = renameInput.value.trim();
    if (!newName || !selectedGroup) return;
    const res = await fetch(`/api/groups/${selectedGroup.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName })
    });
    if (res.ok) {
        renameModal.classList.add('hidden');
        await fetchGroups();
    }
};

// Bulk / Merge logic
function openMoveModal(title, desc, onConfirm) {
    moveModalTitle.innerText = title;
    moveModalDesc.innerText = desc;
    moveTargetGroup = null;
    confirmMoveBtn.disabled = true;
    movePeopleList.innerHTML = '';

    const targets = allGroups.filter(g => g.id !== (isBulkMode ? -1 : selectedGroup.id));
    targets.forEach(group => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-3 p-2 border dark:border-slate-700 rounded cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-700 transition merge-target-item';
        div.onclick = () => {
            moveTargetGroup = group;
            document.querySelectorAll('.merge-target-item').forEach(el => el.classList.remove('merge-target'));
            div.classList.add('merge-target');
            confirmMoveBtn.disabled = false;
        };
        div.innerHTML = `
                    <img src="/api/image?path=${encodeURIComponent(group.thumbnail)}" class="w-10 h-10 rounded-full object-cover">
                    <div><p class="text-sm font-semibold dark:text-slate-200">${group.name}</p></div>
                `;
        movePeopleList.appendChild(div);
    });

    confirmMoveBtn.onclick = onConfirm;
    moveModal.classList.remove('hidden');
}

openMergeBtn.onclick = () => {
    isBulkMode = false;
    openMoveModal(`Merge ${selectedGroup.name}`, `Select target for merge.`, async () => {
        const res = await fetch(`/api/groups/${selectedGroup.id}/merge/${moveTargetGroup.id}`, { method: 'POST' });
        if (res.ok) { moveModal.classList.add('hidden'); selectedGroup = moveTargetGroup; await fetchGroups(); }
    });
};

bulkMoveBtn.onclick = () => {
    isBulkMode = true;
    openMoveModal("Move Selected Photos", `Select person to move ${selectedPhotoIds.length} photos into.`, async () => {
        const res = await fetch(`/api/photos/bulk`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ photo_ids: selectedPhotoIds, target_person_id: moveTargetGroup.id })
        });
        if (res.ok) { moveModal.classList.add('hidden'); clearSelection(); await fetchGroups(); }
    });
};

bulkDeleteBtn.onclick = async () => {
    if (!(await showInfo('Confirm Removal', `Remove ${selectedPhotoIds.length} photos from this group?`, true))) return;
    const res = await fetch(`/api/photos/bulk`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ photo_ids: selectedPhotoIds, target_person_id: null })
    });
    if (res.ok) { clearSelection(); await fetchGroups(); }
};

cancelMoveBtn.onclick = () => moveModal.classList.add('hidden');

exportPersonBtn.onclick = async () => {
    if (!selectedGroup) return;
    const res = await fetch(`/api/groups/${selectedGroup.id}/export`, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'Exported') {
        await showInfo('Export Successful', `Successfully exported ${data.count} photos to: ${data.destination}`);
    } else if (data.status === 'Cancelled') {
        // Do nothing
    } else {
        await showInfo('Export Failed', 'Export failed: ' + (data.detail || 'Unknown error'));
    }
};

deletePersonBtn.onclick = async () => {
    if (!(await showInfo('Confirm Delete', `Delete group "${selectedGroup.name}"?`, true))) return;
    const res = await fetch(`/api/groups/${selectedGroup.id}`, { method: 'DELETE' });
    if (res.ok) {
        selectedGroup = null; controlPanel.classList.add('hidden'); photoGrid.innerHTML = ''; galleryTitle.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-blue-500 inline mr-2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                </svg>
                All Photos
            `; await fetchGroups();
    }
};

settingsBtn.onclick = () => {settingsModal.classList.remove('hidden');console.log('Open settings modal');};
closeSettingsBtn.onclick = () => settingsModal.classList.add('hidden');
settingsOkBtn.onclick = () => settingsModal.classList.add('hidden');

clearCacheBtn.onclick = async () => {
    if (!(await showInfo('Confirm Cache Clear', 'This will remove all cached face embeddings that are not associated with any person. This can help free up disk space but may cause previously identified photos to be reprocessed on next scan. Proceed?', true))) return;
    const res = await fetch('/api/clearcache', { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
        await showInfo('Cache Cleared', `${data.status}: Removed ${data.count} orphaned photo entries.`);
    } else {
        await showInfo('Clear Failed', 'Failed to clear cache.');
    }
};


// Check for active scan on load
pollScanProgress();

fetchGroups();