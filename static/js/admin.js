// ===== ADMIN TEASER JAVASCRIPT =====

class TeaserAdmin {
    constructor() {
        this.config = window.ADMIN_CONFIG || {};
        this.zones = ['left1', 'left2', 'left3', 'center'];
        this.dragDropInstances = new Map();
        this.currentZoneData = {};
        
        this.init();
    }
    
    init() {
        console.log('🔧 TeaserAdmin initialized');
        
        this.initDragAndDrop();
        this.initTabs();
        this.initFormListeners();
        this.loadInitialData();
        
        // Auto-save draft every 30 seconds
        setInterval(() => this.saveDraft(), 30000);
    }
    
    // ===== DRAG & DROP =====
    initDragAndDrop() {
        this.zones.forEach(zone => {
            const dropzone = document.getElementById(`dropzone-${zone}`);
            const fileInput = dropzone?.querySelector('.file-input');
            
            if (dropzone && fileInput) {
                this.setupDropzone(dropzone, fileInput, zone);
            }
        });
        
        // Modal dropzone
        const modalDropzone = document.getElementById('modal-dropzone');
        const modalFileInput = document.getElementById('modal-file-input');
        if (modalDropzone && modalFileInput) {
            this.setupDropzone(modalDropzone, modalFileInput, 'modal');
        }
    }
    
    setupDropzone(dropzone, fileInput, zone) {
        // Click to select files
        dropzone.addEventListener('click', () => {
            fileInput.click();
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.files, zone);
        });
        
        // Drag and drop events
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        
        dropzone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        });
        
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            this.handleFileSelect(e.dataTransfer.files, zone);
        });
    }
    
    async handleFileSelect(files, zone) {
        if (!files || files.length === 0) return;
        
        const formData = new FormData();
        Array.from(files).forEach(file => {
            if (this.isValidMediaFile(file)) {
                formData.append('files', file);
            }
        });
        
        formData.append('zone', zone);
        
        try {
            this.showUploadProgress();
            
            const response = await fetch('/api/admin/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`${result.uploaded_count} fichier(s) uploadé(s)`, 'success');
                
                if (zone === 'modal' && this.config.current_zone) {
                    this.loadZoneContent(this.config.current_zone);
                } else if (zone !== 'modal') {
                    this.loadMediaList(zone);
                    this.updateMockupPreview();
                }
                
                this.markUnsavedChanges();
            } else {
                throw new Error(result.message || 'Upload failed');
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Erreur d\'upload: ' + error.message, 'error');
        } finally {
            this.hideUploadProgress();
        }
    }
    
    isValidMediaFile(file) {
        const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 
                           'video/mp4', 'video/webm', 'video/ogg'];
        const maxSize = 50 * 1024 * 1024; // 50MB
        
        if (!validTypes.includes(file.type)) {
            this.showNotification(`Type de fichier non supporté: ${file.name}`, 'warning');
            return false;
        }
        
        if (file.size > maxSize) {
            this.showNotification(`Fichier trop volumineux: ${file.name}`, 'warning');
            return false;
        }
        
        return true;
    }
    
    // ===== TABS MANAGEMENT =====
    initTabs() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.dataset.tab;
                
                // Update buttons
                tabButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Update content
                tabContents.forEach(content => {
                    content.classList.remove('active');
                    if (content.id === targetTab + '-tab') {
                        content.classList.add('active');
                    }
                });
            });
        });
    }
    
    // ===== FORM LISTENERS =====
    initFormListeners() {
        // Listen to all form inputs for changes
        document.addEventListener('change', (e) => {
            if (e.target.matches('.form-input, .form-select, .form-range')) {
                this.markUnsavedChanges();
                
                // Update range value display
                if (e.target.type === 'range') {
                    const valueSpan = e.target.parentElement.querySelector('.range-value');
                    if (valueSpan) {
                        valueSpan.textContent = Math.round(e.target.value * 100) + '%';
                    }
                }
            }
        });
        
        // Listen to input events for real-time updates
        document.addEventListener('input', (e) => {
            if (e.target.matches('.form-input')) {
                this.markUnsavedChanges();
            }
        });
    }
    
    // ===== DATA LOADING =====
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadCurrentConfig(),
                this.loadAllMediaLists(),
                this.updateMockupPreview(),
                this.checkSystemStatus()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showNotification('Erreur de chargement des données', 'error');
        }
    }
    
    async loadCurrentConfig() {
        try {
            const response = await fetch('/api/admin/config');
            const config = await response.json();
            
            this.populateConfigForms(config);
            console.log('Configuration loaded:', config);
            
        } catch (error) {
            console.error('Error loading config:', error);
        }
    }
    
    populateConfigForms(config) {
        // Weather config
        this.setFormValue('weather_api_key', config.weather_api_key);
        this.setFormValue('weather_location', config.weather_location);
        this.setFormValue('weather_refresh', config.weather_refresh / 60); // convert to minutes
        
        // Tide config
        this.setFormValue('tide_api_key', config.tide_api_key);
        this.setFormValue('tide_lat', config.tide_lat);
        this.setFormValue('tide_lon', config.tide_lon);
        
        // System config
        this.setFormValue('carousel_speed', config.carousel_speed);
        this.setFormValue('auto_play_videos', config.auto_play_videos.toString());
        this.setFormValue('video_volume', config.video_volume);
        this.setFormValue('auto_cleanup', config.auto_cleanup.toString());
        this.setFormValue('cleanup_days', config.cleanup_days);
        this.setFormValue('debug_mode', config.debug_mode.toString());
        
        // Module config
        this.setFormValue('selfie_path', config.selfie_path);
        this.setFormValue('selfie_count', config.selfie_count);
        this.setFormValue('dj_url', config.dj_url);
        this.setFormValue('music_refresh', config.music_refresh);
    }
    
    setFormValue(name, value) {
        const element = document.querySelector(`[name="${name}"]`);
        if (element) {
            if (element.type === 'range') {
                element.value = value;
                const valueSpan = element.parentElement.querySelector('.range-value');
                if (valueSpan) {
                    valueSpan.textContent = Math.round(value * 100) + '%';
                }
            } else {
                element.value = value || '';
            }
        }
    }
    
    async loadAllMediaLists() {
        const promises = this.zones.map(zone => this.loadMediaList(zone));
        await Promise.allSettled(promises);
    }
    
    async loadMediaList(zone) {
        try {
            const response = await fetch(`/api/admin/media/${zone}`);
            const data = await response.json();
            
            this.displayMediaList(zone, data.content || []);
            
        } catch (error) {
            console.error(`Error loading media list for ${zone}:`, error);
        }
    }
    
    displayMediaList(zone, mediaList) {
        const container = document.getElementById(`media-list-${zone}`);
        if (!container) return;
        
        if (mediaList.length === 0) {
            container.innerHTML = '<p class="no-media">Aucun média dans cette zone</p>';
            return;
        }
        
        container.innerHTML = mediaList.map(item => this.createMediaItem(item, zone)).join('');
        
        // Update mockup preview count
        const preview = document.getElementById(`${zone}-preview`);
        if (preview) {
            const countElement = preview.querySelector('.content-count');
            if (countElement) {
                countElement.textContent = `${mediaList.length} élément${mediaList.length > 1 ? 's' : ''}`;
            }
        }
    }
    
    createMediaItem(item, zone) {
        const isImage = item.type === 'image';
        const thumbnail = isImage ? item.src : '/static/icons/video-placeholder.png';
        
        return `
            <div class="media-item" data-id="${item.id}">
                <div class="media-thumbnail">
                    <img src="${thumbnail}" alt="${item.title || 'Media'}" loading="lazy">
                    ${!isImage ? '<i class="fas fa-play-circle video-indicator"></i>' : ''}
                </div>
                <div class="media-info">
                    <div class="media-title">${item.title || item.filename}</div>
                    <div class="media-meta">
                        <span class="media-type">${item.type}</span>
                        <span class="media-duration">${item.duration}s</span>
                    </div>
                </div>
                <div class="media-actions">
                    <button class="btn-icon" onclick="editMediaItem('${zone}', ${item.id})" title="Éditer">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon btn-danger" onclick="deleteMediaItem('${zone}', ${item.id})" title="Supprimer">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    // ===== MOCKUP MANAGEMENT =====
    async updateMockupPreview() {
        try {
            // Load content counts for each zone
            for (const zone of this.zones) {
                const response = await fetch(`/api/admin/media/${zone}`);
                const data = await response.json();
                
                this.updateZonePreview(zone, data.content || []);
            }
            
            // Update widget status
            this.updateWidgetStatus();
            
        } catch (error) {
            console.error('Error updating mockup preview:', error);
        }
    }
    
    updateZonePreview(zone, content) {
        const preview = document.getElementById(`${zone}-preview`);
        if (!preview) return;
        
        const count = content.length;
        const countElement = preview.querySelector('.content-count');
        const iconElement = preview.querySelector('i');
        const spanElement = preview.querySelector('span');
        
        if (countElement) {
            countElement.textContent = `${count} élément${count !== 1 ? 's' : ''}`;
        }
        
        // Update visual state
        if (count > 0) {
            iconElement.className = 'fas fa-images';
            preview.parentElement.classList.add('has-content');
            
            // Show first item as preview if available
            if (content[0] && content[0].type === 'image') {
                preview.style.backgroundImage = `url(${content[0].src})`;
                preview.style.backgroundSize = 'cover';
                preview.style.backgroundPosition = 'center';
            }
        } else {
            iconElement.className = 'fas fa-plus';
            preview.parentElement.classList.remove('has-content');
            preview.style.backgroundImage = '';
        }
    }
    
    async updateWidgetStatus() {
        try {
            const response = await fetch('/api/admin/widget-status');
            const status = await response.json();
            
            this.setWidgetStatus('weather-widget-status', status.weather);
            this.setWidgetStatus('selfie-widget-status', status.selfie);
            this.setWidgetStatus('music-widget-status', status.music);
            
        } catch (error) {
            console.error('Error updating widget status:', error);
        }
    }
    
    setWidgetStatus(elementId, status) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const icon = element.querySelector('i');
        icon.className = `fas fa-circle ${status}`;
    }
    
    // ===== SYSTEM STATUS =====
    async checkSystemStatus() {
        try {
            const response = await fetch('/api/admin/system-status');
            const status = await response.json();
            
            // Update sidebar status
            document.getElementById('server-status').textContent = status.server ? 'En ligne' : 'Hors ligne';
            document.getElementById('server-status').className = `status-value ${status.server ? 'online' : 'offline'}`;
            
            document.getElementById('weather-status').textContent = status.apis.weather ? 'OK' : 'Erreur';
            document.getElementById('weather-status').className = `status-value ${status.apis.weather ? 'online' : 'offline'}`;
            
            document.getElementById('modules-status').textContent = `${status.modules.active}/${status.modules.total}`;
            document.getElementById('modules-status').className = `status-value ${status.modules.active > 0 ? 'online' : 'offline'}`;
            
            // Update module cards
            document.getElementById('selfie-module-status').querySelector('i').className = 
                `fas fa-circle ${status.modules.selfie ? 'online' : 'offline'}`;
            document.getElementById('dj-module-status').querySelector('i').className = 
                `fas fa-circle ${status.modules.dj ? 'online' : 'offline'}`;
            
        } catch (error) {
            console.error('Error checking system status:', error);
        }
    }
    
    // ===== ZONE CONFIGURATION =====
    async loadZoneContent(zone) {
        try {
            const response = await fetch(`/api/admin/zone/${zone}`);
            const data = await response.json();
            
            this.currentZoneData = data;
            this.populateZoneModal(data);
            
        } catch (error) {
            console.error('Error loading zone content:', error);
            this.showNotification('Erreur de chargement de la zone', 'error');
        }
    }
    
    populateZoneModal(data) {
        // Populate zone settings
        document.getElementById('zone-title').value = data.title || '';
        document.getElementById('zone-duration').value = data.duration || 5;
        document.getElementById('zone-enabled').value = data.enabled ? 'true' : 'false';
        
        // Populate content list
        const contentList = document.getElementById('zone-content-list');
        if (data.content && data.content.length > 0) {
            contentList.innerHTML = data.content.map(item => this.createZoneContentItem(item)).join('');
            this.initSortableContentList();
        } else {
            contentList.innerHTML = '<p class="no-content">Aucun contenu dans cette zone</p>';
        }
    }
    
    createZoneContentItem(item) {
        const thumbnail = item.type === 'image' ? item.src : '/static/icons/video-placeholder.png';
        
        return `
            <div class="zone-content-item" data-id="${item.id}">
                <div class="drag-handle">
                    <i class="fas fa-grip-vertical"></i>
                </div>
                <div class="item-thumbnail">
                    <img src="${thumbnail}" alt="${item.title || 'Content'}">
                    ${item.type === 'video' ? '<i class="fas fa-play-circle"></i>' : ''}
                </div>
                <div class="item-info">
                    <div class="item-title">${item.title || item.filename}</div>
                    <div class="item-meta">
                        <span>${item.type}</span> • <span>${item.duration}s</span>
                        ${item.order ? ` • Position ${item.order}` : ''}
                    </div>
                </div>
                <div class="item-actions">
                    <button class="btn-icon" onclick="editZoneContentItem(${item.id})" title="Éditer">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon btn-danger" onclick="deleteZoneContentItem(${item.id})" title="Supprimer">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    initSortableContentList() {
        const contentList = document.getElementById('zone-content-list');
        if (!contentList) return;
        
        new Sortable(contentList, {
            handle: '.drag-handle',
            animation: 150,
            ghostClass: 'sortable-ghost',
            onEnd: (evt) => {
                this.markUnsavedChanges();
                this.updateContentOrder();
            }
        });
    }
    
    updateContentOrder() {
        const items = document.querySelectorAll('.zone-content-item');
        const newOrder = Array.from(items).map((item, index) => ({
            id: parseInt(item.dataset.id),
            order: index
        }));
        
        // Store the new order for saving
        this.currentZoneData.newOrder = newOrder;
    }
    
    // ===== SAVE/LOAD FUNCTIONS =====
    gatherAllConfig() {
        return {
            weather: this.gatherFormData('weather-config-form'),
            tide: this.gatherFormData('tide-config-form'),
            system: this.gatherSystemConfig(),
            modules: this.gatherModuleConfig(),
            zones: this.gatherZoneConfigs()
        };
    }
    
    gatherFormData(formId) {
        const form = document.getElementById(formId);
        if (!form) return {};
        
        const formData = new FormData(form);
        const data = {};
        
        for (const [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        return data;
    }
    
    gatherSystemConfig() {
        return {
            carousel_speed: parseInt(document.querySelector('[name="carousel_speed"]').value),
            auto_play_videos: document.querySelector('[name="auto_play_videos"]').value === 'true',
            video_volume: parseFloat(document.querySelector('[name="video_volume"]').value),
            auto_cleanup: document.querySelector('[name="auto_cleanup"]').value === 'true',
            cleanup_days: parseInt(document.querySelector('[name="cleanup_days"]').value),
            debug_mode: document.querySelector('[name="debug_mode"]').value === 'true'
        };
    }
    
    gatherModuleConfig() {
        return {
            selfie_path: document.querySelector('[name="selfie_path"]').value,
            selfie_count: parseInt(document.querySelector('[name="selfie_count"]').value),
            dj_url: document.querySelector('[name="dj_url"]').value,
            music_refresh: parseInt(document.querySelector('[name="music_refresh"]').value)
        };
    }
    
    gatherZoneConfigs() {
        // This would gather configurations from all zones
        // For now, return current zone if being edited
        const zones = {};
        
        if (this.config.current_zone && this.currentZoneData) {
            zones[this.config.current_zone] = {
                title: document.getElementById('zone-title')?.value,
                duration: parseInt(document.getElementById('zone-duration')?.value || 5),
                enabled: document.getElementById('zone-enabled')?.value === 'true',
                content_order: this.currentZoneData.newOrder
            };
        }
        
        return zones;
    }
    
    gatherZoneConfig() {
        return {
            title: document.getElementById('zone-title').value,
            duration: parseInt(document.getElementById('zone-duration').value),
            enabled: document.getElementById('zone-enabled').value === 'true',
            content_order: this.currentZoneData.newOrder || []
        };
    }
    
    async saveDraft() {
        if (!this.config.unsaved_changes) return;
        
        try {
            const config = this.gatherAllConfig();
            await fetch('/api/admin/save-draft', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            console.log('Draft saved automatically');
            
        } catch (error) {
            console.error('Error saving draft:', error);
        }
    }
    
    // ===== UI HELPERS =====
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => notification.classList.add('show'), 100);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }
    
    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-triangle',
            warning: 'exclamation-circle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    showUploadProgress() {
        // Create or show upload progress indicator
        let progress = document.getElementById('upload-progress');
        if (!progress) {
            progress = document.createElement('div');
            progress.id = 'upload-progress';
            progress.className = 'upload-progress';
            progress.innerHTML = `
                <div class="progress-content">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Upload en cours...</span>
                </div>
            `;
            document.body.appendChild(progress);
        }
        progress.style.display = 'flex';
    }
    
    hideUploadProgress() {
        const progress = document.getElementById('upload-progress');
        if (progress) {
            progress.style.display = 'none';
        }
    }
    
    markUnsavedChanges() {
        this.config.unsaved_changes = true;
        const saveBtn = document.getElementById('save-btn');
        if (saveBtn) {
            saveBtn.classList.add('unsaved');
        }
    }
    
    markChangesSaved() {
        this.config.unsaved_changes = false;
        const saveBtn = document.getElementById('save-btn');
        if (saveBtn) {
            saveBtn.classList.remove('unsaved');
        }
    }
}

// ===== GLOBAL FUNCTIONS =====

// let adminInstance;

function initAdminInterface() {
    adminInstance = new TeaserAdmin();
}

function openZoneConfig(zone) {
    window.ADMIN_CONFIG.current_zone = zone;
    document.getElementById('zone-modal-title').textContent = `Configuration ${zone.toUpperCase()}`;
    adminInstance.loadZoneContent(zone);
    openModal('zone-config-modal');
}

function saveZoneConfig() {
    if (!adminInstance) return;
    
    const zone = window.ADMIN_CONFIG.current_zone;
    const config = adminInstance.gatherZoneConfig();
    
    fetch(`/api/admin/zone/${zone}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            adminInstance.showNotification('Configuration sauvegardée', 'success');
            closeModal('zone-config-modal');
            adminInstance.updateMockupPreview();
            adminInstance.markChangesSaved();
        } else {
            throw new Error(result.message || 'Erreur de sauvegarde');
        }
    })
    .catch(error => {
        console.error('Save error:', error);
        adminInstance.showNotification('Erreur: ' + error.message, 'error');
    });
}

function saveAllConfig() {
    if (!adminInstance) return;
    
    const config = adminInstance.gatherAllConfig();
    
    fetch('/api/admin/save-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            adminInstance.showNotification('Configuration complète sauvegardée', 'success');
            adminInstance.markChangesSaved();
        } else {
            throw new Error(result.message || 'Erreur de sauvegarde globale');
        }
    })
    .catch(error => {
        console.error('Global save error:', error);
        adminInstance.showNotification('Erreur: ' + error.message, 'error');
    });
}

// Weather/Tide/Module testing functions
async function testWeatherAPI() {
    const apiKey = document.querySelector('[name="weather_api_key"]').value;
    const location = document.querySelector('[name="weather_location"]').value;
    
    if (!apiKey || !location) {
        adminInstance.showNotification('Veuillez remplir la clé API et la localisation', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/admin/test-weather', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey, location: location })
        });
        
        const result = await response.json();
        
        if (result.success) {
            adminInstance.showNotification('API Météo connectée avec succès', 'success');
        } else {
            throw new Error(result.message);
        }
        
    } catch (error) {
        adminInstance.showNotification('Erreur API Météo: ' + error.message, 'error');
    }
}

async function testTideAPI() {
    const apiKey = document.querySelector('[name="tide_api_key"]').value;
    const lat = document.querySelector('[name="tide_lat"]').value;
    const lon = document.querySelector('[name="tide_lon"]').value;
    
    if (!apiKey || !lat || !lon) {
        adminInstance.showNotification('Veuillez remplir tous les champs', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/admin/test-tide', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey, lat: parseFloat(lat), lon: parseFloat(lon) })
        });
        
        const result = await response.json();
        
        if (result.success) {
            adminInstance.showNotification('API Marées connectée avec succès', 'success');
        } else {
            throw new Error(result.message);
        }
        
    } catch (error) {
        adminInstance.showNotification('Erreur API Marées: ' + error.message, 'error');
    }
}

async function testSelfieModule() {
    const selfiePath = document.querySelector('[name="selfie_path"]').value;
    
    try {
        const response = await fetch('/api/admin/test-selfie', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: selfiePath })
        });
        
        const result = await response.json();
        
        if (result.success) {
            adminInstance.showNotification(`Module Selfie OK (${result.count} photos trouvées)`, 'success');
        } else {
            throw new Error(result.message);
        }
        
    } catch (error) {
        adminInstance.showNotification('Erreur Module Selfie: ' + error.message, 'error');
    }
}

async function testDJModule() {
    const djUrl = document.querySelector('[name="dj_url"]').value;
    
    if (!djUrl) {
        adminInstance.showNotification('Veuillez remplir l\'URL du module DJ', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/admin/test-dj', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: djUrl })
        });
        
        const result = await response.json();
        
        if (result.success) {
            adminInstance.showNotification('Module DJ/Jukebox connecté avec succès', 'success');
        } else {
            throw new Error(result.message);
        }
        
    } catch (error) {
        adminInstance.showNotification('Erreur Module DJ: ' + error.message, 'error');
    }
}

// Utility functions for media management
async function deleteMediaItem(zone, itemId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cet élément ?')) return;
    
    try {
        const response = await fetch(`/api/admin/media/${zone}/${itemId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            adminInstance.showNotification('Élément supprimé', 'success');
            adminInstance.loadMediaList(zone);
            adminInstance.updateMockupPreview();
            adminInstance.markUnsavedChanges();
        } else {
            throw new Error(result.message);
        }
        
    } catch (error) {
        adminInstance.showNotification('Erreur de suppression: ' + error.message, 'error');
    }
}

function editMediaItem(zone, itemId) {
    // Open edit modal for specific media item
    console.log('Edit media item:', zone, itemId);
    // Implementation would open a modal to edit item properties
}

function addUrlContent() {
    const url = document.getElementById('url-input').value;
    const title = document.getElementById('url-title').value;
    const zone = window.ADMIN_CONFIG.current_zone;
    
    if (!url || !zone) {
        adminInstance.showNotification('Veuillez remplir l\'URL', 'warning');
        return;
    }
    
    fetch('/api/admin/add-url-content', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            zone: zone,
            url: url,
            title: title
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            adminInstance.showNotification('URL ajoutée avec succès', 'success');
            document.getElementById('url-input').value = '';
            document.getElementById('url-title').value = '';
            adminInstance.loadZoneContent(zone);
            adminInstance.markUnsavedChanges();
        } else {
            throw new Error(result.message);
        }
    })
    .catch(error => {
        adminInstance.showNotification('Erreur: ' + error.message, 'error');
    });
}

// System functions
async function runCleanup() {
    if (!confirm('Êtes-vous sûr de vouloir nettoyer les fichiers anciens ?')) return;
    
    try {
        const response = await fetch('/api/admin/cleanup', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            adminInstance.showNotification(`Nettoyage terminé: ${result.deleted_files} fichiers supprimés`, 'success');
        } else {
            throw new Error(result.message);
        }
        
    } catch (error) {
        adminInstance.showNotification('Erreur de nettoyage: ' + error.message, 'error');
    }
}

function viewLogs() {
    window.open('/api/admin/logs', '_blank');
}

function downloadBackup() {
    window.location.href = '/api/admin/backup';
}