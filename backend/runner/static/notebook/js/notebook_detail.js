const notebookDetail = {
    config: null,
    notebookElement: null,
    sessionId: null,
    sessionPromise: null,
    cellStatuses: {},
    storageEnabled: undefined,
    inactivityTimers: {
        prompt: null,
        ban: null,
    },
    inactivityOverlay: null,
    lastActivityTs: null,

    sanitizeUrl(value) {
        if (typeof value !== 'string') {
            return '';
        }
        const trimmed = value.trim();
        if (!trimmed || trimmed === 'undefined' || trimmed === 'null') {
            return '';
        }
        return trimmed;
    },

    getSessionStorageKey() {
        return `notebook:${this.config?.notebookId}:session-id`;
    },

    getStatusStorageKey() {
        return `notebook:${this.config?.notebookId}:cell-statuses`;
    },

    isStorageAvailable() {
        if (typeof window === 'undefined') {
            return false;
        }
        if (typeof this.storageEnabled === 'boolean') {
            return this.storageEnabled;
        }
        try {
            const testKey = '__nb_storage_test__';
            window.localStorage.setItem(testKey, '1');
            window.localStorage.removeItem(testKey);
            this.storageEnabled = true;
        } catch (error) {
            console.warn('LocalStorage недоступен:', error);
            this.storageEnabled = false;
        }
        return this.storageEnabled;
    },

    readStorage(key) {
        if (!this.isStorageAvailable()) {
            return null;
        }
        try {
            return window.localStorage.getItem(key);
        } catch (error) {
            console.warn('Не удалось прочитать localStorage', error);
            return null;
        }
    },

    writeStorage(key, value) {
        if (!this.isStorageAvailable()) {
            return;
        }
        try {
            window.localStorage.setItem(key, value);
        } catch (error) {
            console.warn('Не удалось записать localStorage', error);
        }
    },

    removeStorage(key) {
        if (!this.isStorageAvailable()) {
            return;
        }
        try {
            window.localStorage.removeItem(key);
        } catch (error) {
            console.warn('Не удалось очистить localStorage', error);
        }
    },

    getStoredSessionId() {
        return this.readStorage(this.getSessionStorageKey());
    },

    storeSessionId(sessionId) {
        if (sessionId) {
            this.writeStorage(this.getSessionStorageKey(), sessionId);
        }
    },

    clearStoredSessionId() {
        this.removeStorage(this.getSessionStorageKey());
    },

    loadCellStatuses() {
        const raw = this.readStorage(this.getStatusStorageKey());
        if (!raw) {
            return {};
        }
        try {
            const parsed = JSON.parse(raw);
            if (!parsed || typeof parsed !== 'object') {
                return {};
            }
            const normalized = {};
            Object.entries(parsed).forEach(([cellId, value]) => {
                if (!cellId) {
                    return;
                }
                if (typeof value === 'string') {
                    normalized[cellId] = { state: value };
                } else if (value && typeof value === 'object' && value.state) {
                    normalized[cellId] = {
                        state: value.state,
                        meta: value.meta && typeof value.meta === 'object' ? value.meta : null,
                    };
                }
            });
            return normalized;
        } catch (_error) {
            return {};
        }
    },

    persistCellStatuses() {
        if (!this.cellStatuses || Object.keys(this.cellStatuses).length === 0) {
            this.removeStorage(this.getStatusStorageKey());
            return;
        }
        const payload = JSON.stringify(this.cellStatuses);
        this.writeStorage(this.getStatusStorageKey(), payload);
    },

    describeStatus(status, meta) {
        switch (status) {
            case 'running':
                return 'Выполняется...';
            case 'success': {
                const label = this.formatDuration(meta?.durationMs);
                return label ? `Готово: ${label}` : 'Готово';
            }
            case 'error':
                return 'Ошибка';
            case 'reset':
                return 'Нужен повторный запуск';
            default:
                return 'Ожидание';
        }
    },

    formatDuration(ms) {
        if (typeof ms !== 'number' || Number.isNaN(ms)) {
            return '';
        }
        if (ms >= 1000) {
            return `${(ms / 1000).toFixed(1)} с`;
        }
        return `${Math.round(ms)} мс`;
    },

    updateCellStatusElement(cellId, status, meta) {
        const cellElement = document.querySelector(`[data-cell-id="${cellId}"]`);
        if (!cellElement) {
            return;
        }
        const statusElement = cellElement.querySelector('[data-cell-status]');
        if (!statusElement) {
            return;
        }
        const finalStatus = status || 'idle';
        statusElement.dataset.status = finalStatus;
        statusElement.textContent = this.describeStatus(finalStatus, meta);
    },

    setCellStatus(cellId, status, meta) {
        if (!cellId) {
            return;
        }
        if (!status || status === 'idle') {
            delete this.cellStatuses[cellId];
        } else {
            this.cellStatuses[cellId] = {
                state: status,
                meta: meta || null,
            };
        }
        this.persistCellStatuses();
        this.updateCellStatusElement(cellId, status, meta);
    },

    resetAllCellStatuses(status = 'reset') {
        const cells = document.querySelectorAll('[data-cell-id]');
        const nextStatuses = {};
        cells.forEach((cell) => {
            const cellId = cell.dataset.cellId;
            if (!cellId) {
                return;
            }
            const hasStatus = !!cell.querySelector('[data-cell-status]');
            if (!hasStatus) {
                return;
            }
            if (status !== 'idle') {
                nextStatuses[cellId] = { state: status };
            }
            this.updateCellStatusElement(cellId, status === 'idle' ? 'idle' : status, null);
        });
        this.cellStatuses = nextStatuses;
        this.persistCellStatuses();
    },

    applyStatusesToExistingCells() {
        const elements = document.querySelectorAll('[data-cell-status]');
        elements.forEach((el) => {
            const cellElement = el.closest('[data-cell-id]');
            if (!cellElement) {
                return;
            }
            const cellId = cellElement.dataset.cellId;
            const record = this.cellStatuses[cellId];
            const status = record?.state || 'idle';
            this.updateCellStatusElement(cellId, status, record?.meta);
        });
    },

    initActivityTracking() {
        this.lastActivityTs = Date.now();
        const events = ['click', 'keydown', 'mousemove', 'scroll', 'touchstart'];
        this.activityHandler = this.markActivity.bind(this);
        events.forEach((evt) => {
            document.addEventListener(evt, this.activityHandler, { passive: true });
        });
        this.scheduleInactivityPrompt();
    },

    markActivity() {
        this.lastActivityTs = Date.now();
        this.hideInactivityPrompt();
        this.scheduleInactivityPrompt();
    },

    scheduleInactivityPrompt() {
        if (this.inactivityTimers.prompt) {
            clearTimeout(this.inactivityTimers.prompt);
        }
        this.inactivityTimers.prompt = window.setTimeout(
            () => this.showInactivityPrompt(),
            30 * 60 * 1000,
        );
    },

    showInactivityPrompt() {
        if (!this.inactivityOverlay) {
            this.inactivityOverlay = this.buildInactivityOverlay();
            document.body.appendChild(this.inactivityOverlay);
        }
        this.inactivityOverlay.hidden = false;
        if (this.inactivityTimers.ban) {
            clearTimeout(this.inactivityTimers.ban);
        }
        this.inactivityTimers.ban = window.setTimeout(
            () => this.banSession(),
            10 * 60 * 1000,
        );
    },

    hideInactivityPrompt() {
        if (this.inactivityTimers.ban) {
            clearTimeout(this.inactivityTimers.ban);
            this.inactivityTimers.ban = null;
        }
        if (this.inactivityOverlay) {
            this.inactivityOverlay.hidden = true;
        }
    },

    buildInactivityOverlay() {
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.inset = '0';
        overlay.style.background = 'rgba(0, 0, 0, 0.4)';
        overlay.style.display = 'flex';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.zIndex = '9999';

        const modal = document.createElement('div');
        modal.style.background = '#fff';
        modal.style.padding = '24px';
        modal.style.borderRadius = '8px';
        modal.style.boxShadow = '0 10px 30px rgba(0,0,0,0.2)';
        modal.style.maxWidth = '320px';
        modal.style.textAlign = 'center';

        const title = document.createElement('h3');
        title.textContent = 'Вы ещё здесь?';
        title.style.marginTop = '0';

        const text = document.createElement('p');
        text.textContent = 'Сессия будет перезапущена через 10 минут бездействия.';

        const button = document.createElement('button');
        button.textContent = 'Да, продолжаю';
        button.style.marginTop = '12px';
        button.addEventListener('click', () => this.handlePresenceConfirm());

        modal.appendChild(title);
        modal.appendChild(text);
        modal.appendChild(button);
        overlay.appendChild(modal);
        overlay.hidden = true;
        return overlay;
    },

    handlePresenceConfirm() {
        this.hideInactivityPrompt();
        this.markActivity();
    },

    async banSession() {
        this.hideInactivityPrompt();
        try {
            await this.resetSession({ silent: true, reason: 'ban' });
            alert('Сессия остановлена из-за длительного бездействия.');
        } catch (error) {
            console.error('Не удалось завершить сессию из-за бездействия:', error);
        }
    },

    init(config) {
        this.config = config;
        this.notebookElement = document.querySelector(`[data-notebook-id="${config.notebookId}"]`);
        this.deleteUrlTemplate = this.notebookElement?.dataset.deleteUrlTemplate || '';
        this.saveOutputUrlTemplate = this.notebookElement?.dataset.saveOutputUrlTemplate || '';
        this.runCellUrl = this.sanitizeUrl(config.runCellUrl) || this.sanitizeUrl(this.notebookElement?.dataset.runCellUrl);
        this.sessionCreateUrl = this.sanitizeUrl(config.sessionCreateUrl) || this.sanitizeUrl(this.notebookElement?.dataset.sessionCreateUrl);
        this.sessionResetUrl = this.sanitizeUrl(config.sessionResetUrl) || this.sanitizeUrl(this.notebookElement?.dataset.sessionResetUrl);
        this.cellStatuses = this.loadCellStatuses();
        this.bindEvents();
        this.initializeCells();
        this.applyStatusesToExistingCells();
        this.initActivityTracking();
        this.ensureSession().catch((error) => {
            console.error('Не удалось создать сессию ноутбука:', error);
            alert('Не удалось создать сессию ноутбука. Попробуйте перезагрузить страницу.');
        });
    },

    buildCellUrl(template, cellId) {
        if (!template) {
            return '';
        }

        const placeholderRegex = /\/0(\/|$)/;

        if (!placeholderRegex.test(template)) {
            return '';
        }

        return template.replace(placeholderRegex, (_match, separator) => `/${cellId}${separator}`);
    },

    bindEvents() {
        if (this.notebookElement) {
            this.notebookElement.addEventListener('click', this.handleNotebookClick.bind(this));
        }

        const deleteForm = document.getElementById('delete-notebook-form');
        if (deleteForm) {
            deleteForm.addEventListener('submit', (event) => {
                if (!confirm('Удалить ноутбук?')) {
                    event.preventDefault();
                }
            });
        }
    },

    handleNotebookClick(e) {
        const actionTarget = e.target.closest('[data-action]');

        if (!actionTarget || !this.notebookElement?.contains(actionTarget)) {
            return;
        }

        const action = actionTarget.dataset.action;
        const cellElement = actionTarget.closest('[data-cell-id]');
        const cellId = cellElement ? cellElement.dataset.cellId : null;

        if (action === 'delete-notebook') {
            e.preventDefault();
            this.deleteNotebook(actionTarget);
        }
        else if (action === 'create-cell') {
            this.createCell();
        }
        else if (action === 'create-latex-cell') {
            this.createCell({ payload: { type: 'latex' } });
        }
        else if (action === 'run-cell' && cellId) {
            this.runCell(cellId);
        }
        else if (action === 'delete-cell' && cellId) {
            this.deleteCell(cellId, cellElement);
        }
        else if (action === 'edit-latex' && cellId) {
            this.startLatexEdit(cellElement);
        }
        else if (action === 'save-latex' && cellId) {
            this.saveLatexCell(cellId, cellElement);
        }
        else if (action === 'cancel-latex' && cellId) {
            this.cancelLatexEdit(cellElement);
        }
        else if (action === 'reset-session') {
            this.resetSession();
        }
    },

    async ensureSession(options = {}) {
        const { force = false } = options;

        if (force) {
            this.clearStoredSessionId();
            this.sessionId = null;
        }

        if (this.sessionId && !force) {
            return this.sessionId;
        }

        if (!force) {
            const stored = this.getStoredSessionId();
            if (stored) {
                this.sessionId = stored;
                return stored;
            }
        }

        if (!this.sessionPromise) {
            this.sessionPromise = this.createSession();
        }

        return this.sessionPromise;
    },

    async createSession() {
        if (!this.sessionCreateUrl) {
            throw new Error('URL создания сессии недоступен');
        }

        try {
            const response = await fetch(this.sessionCreateUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken
                },
                body: JSON.stringify({ notebook_id: this.config.notebookId })
            });

            const data = await response.json();

            if (!response.ok) {
                const message = data?.detail || data?.message || 'Не удалось создать сессию';
                throw new Error(message);
            }

            this.sessionId = data.session_id;
            this.storeSessionId(this.sessionId);
            return this.sessionId;
        } catch (error) {
            this.sessionId = null;
            throw error;
        } finally {
            this.sessionPromise = null;
        }
    },

    async resetSession(options = {}) {
        const { silent = false, reason = 'user' } = options;
        try {
            if (reason !== 'ban') {
                this.markActivity();
            }
            const sessionId = await this.ensureSession();
            if (!sessionId) {
                throw new Error('Сессия не инициализирована');
            }
            if (!this.sessionResetUrl) {
                throw new Error('URL сброса сессии недоступен');
            }

            const response = await fetch(this.sessionResetUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken
                },
                body: JSON.stringify({ session_id: sessionId })
            });

            const data = await response.json();
            if (!response.ok) {
                const message = data?.detail || data?.message || 'Не удалось сбросить сессию';
                throw new Error(message);
            }

            this.clearStoredSessionId();
            this.sessionId = null;
            await this.ensureSession({ force: true });
            this.clearOutputsAfterReset();
            this.resetAllCellStatuses('reset');
            if (!silent && reason !== 'ban') {
                alert('Сессия перезапущена. Все переменные очищены.');
            }
        } catch (error) {
            console.error('Ошибка сброса сессии:', error);
            if (!silent) {
                alert('Не удалось перезапустить сессию: ' + (error?.message || error));
            }
        }
    },

    clearOutputsAfterReset() {
        const outputs = document.querySelectorAll('.cell .output');
        outputs.forEach((outputElement) => {
            const previousWrapper = outputElement.querySelector('.output-previous');
            const previousHtml = previousWrapper?.innerHTML || outputElement.innerHTML || '<div class="output-empty">Нет вывода</div>';
            outputElement.innerHTML = `
                <div class="output-reset-note">Нужен повторный запуск. Ниже показан вывод предыдущей сессии.</div>
                <div class="output-previous">${previousHtml}</div>
            `;
            outputElement.classList.add('output');
            outputElement.classList.add('stale');
            const cellElement = outputElement.closest('[data-cell-id]');
            const cellId = cellElement?.dataset.cellId;
            if (cellId) {
                this.setCellStatus(cellId, 'reset');
            }
        });
    },

    async createCell(options = {}) {
        const { urlKey = 'createCellUrl', payload = null } = options;

        try {
            const createCellUrl = this.notebookElement.dataset[urlKey];

            if (!createCellUrl) {
                throw new Error('URL создания ячейки недоступен');
            }

            const headers = {
                'X-CSRFToken': this.config.csrfToken
            };

            const requestInit = {
                method: 'POST',
                headers
            };

            if (payload) {
                headers['Content-Type'] = 'application/json';
                requestInit.body = JSON.stringify(payload);
            }

            const response = await fetch(createCellUrl, requestInit);

            if (!response.ok) throw new Error('HTTP error ' + response.status);

            const html = await response.text();
            const container = document.getElementById('cells-container');

            if (!container) {
                throw new Error('Контейнер для ячеек не найден');
            }

            container.insertAdjacentHTML('beforeend', html);
            const newCell = container.lastElementChild;
            if (newCell) {
                this.initializeCell(newCell);
                const newCellId = newCell.dataset?.cellId;
                if (newCellId) {
                    const record = this.cellStatuses[newCellId];
                    const status = record?.state || 'idle';
                    this.updateCellStatusElement(newCellId, status, record?.meta);
                }
            }

        } catch (error) {
            console.error('Ошибка:', error);
            alert('Ошибка при создании ячейки: ' + error.message);
        }
    },

    async runCell(cellId) {
        const cellElement = document.querySelector(`[data-cell-id="${cellId}"]`);
        if (!cellElement) {
            return;
        }

        const textarea = cellElement.querySelector('textarea');
        const outputElement = document.getElementById(`output-${cellId}`);
        const saveOutputUrl = this.buildCellUrl(this.saveOutputUrlTemplate, cellId);
        const runCellUrl = this.runCellUrl;

        if (!textarea || !outputElement) {
            return;
        }

        const cellNumericId = Number(cellId);
        if (Number.isNaN(cellNumericId)) {
            alert('Некорректный идентификатор ячейки');
            return;
        }

        if (!runCellUrl) {
            alert('URL запуска ячейки недоступен');
            return;
        }

        const sessionId = await this.ensureSession().catch((error) => {
            console.error('Сессия недоступна:', error);
            alert('Сессия недоступна. Попробуйте перезагрузить страницу.');
            return null;
        });

        if (!sessionId) {
            return;
        }

        const code = textarea.value;
        this.setCellStatus(cellId, 'running');
        this.markActivity();
        await this.saveCellState(cellId, code, outputElement.innerHTML, saveOutputUrl);

        this.renderArtifacts(cellId, []);
        outputElement.innerHTML = '<div class="output-loading">Выполнение...</div>';
        outputElement.className = 'output running';
        const startedAt = typeof performance !== 'undefined' ? performance.now() : Date.now();

        try {
            const response = await fetch(runCellUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    cell_id: cellNumericId
                })
            });

            const data = await response.json();

            if (!response.ok) {
                const message = data?.detail || data?.error || 'Не удалось выполнить ячейку';
                throw new Error(message);
            }

            const formattedOutput = NotebookUtils.formatCellRunResult(data);
            outputElement.innerHTML = formattedOutput;
            outputElement.className = data.error ? 'output error' : 'output success';
            this.renderArtifacts(cellId, []);
            const finalStatus = data.error ? 'error' : 'success';
            const durationMs = Math.max(
                0,
                (typeof performance !== 'undefined' ? performance.now() : Date.now()) - startedAt,
            );
            const meta = finalStatus === 'success' ? { durationMs } : null;
            this.setCellStatus(cellId, finalStatus, meta);

            await this.saveCellState(cellId, code, formattedOutput, saveOutputUrl);
        } catch (error) {
            console.error('Ошибка выполнения ячейки:', error);
            const message = error?.message || 'Не удалось выполнить ячейку';
            const errorHtml = `<div class="output-error"><strong>Ошибка:</strong> ${NotebookUtils.escapeHtml(message)}</div>`;
            outputElement.innerHTML = errorHtml;
            outputElement.className = 'output error';
            this.renderArtifacts(cellId, []);
            this.setCellStatus(cellId, 'error');
            await this.saveCellState(cellId, code, errorHtml, saveOutputUrl);
        }
    },

    async saveCellState(cellId, code, outputHtml, saveOutputUrl) {
        const result = await NotebookUtils.saveCellOutput(
            this.config.notebookId,
            cellId,
            code,
            outputHtml || '',
            this.config.csrfToken,
            saveOutputUrl
        );

        if (!result.ok) {
            console.warn('Не удалось сохранить состояние ячейки', result.error);
        }
    },

    renderArtifacts(cellId, artifacts) {
        const container = document.getElementById(`artifacts-${cellId}`);

        if (!container) {
            return;
        }

        if (!Array.isArray(artifacts) || artifacts.length === 0) {
            container.innerHTML = '';
            container.classList.remove('has-artifacts');
            return;
        }

        const items = artifacts.map(artifact => {
            const name = NotebookUtils.escapeHtml(artifact?.name || 'artifact');
            const url = typeof artifact?.url === 'string' ? encodeURI(artifact.url) : '#';

            return `<li><a href="${url}" download target="_blank" rel="noopener noreferrer">${name}</a></li>`;
        }).join('');

        container.innerHTML = `
            <div class="artifacts-title">Вложения</div>
            <ul class="artifacts-list">${items}</ul>
        `;
        container.classList.add('has-artifacts');
    },

    async deleteCell(cellId, cellElement) {
        if (!confirm('Удалить ячейку?')) return;

        try {
            const deleteUrl = this.buildCellUrl(this.deleteUrlTemplate, cellId);

            if (!deleteUrl) {
                throw new Error('URL удаления ячейки недоступен');
            }

            const response = await fetch(deleteUrl, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.config.csrfToken
                }
            });

            if (!response.ok) throw new Error('HTTP error ' + response.status);

            cellElement.remove();
            if (this.cellStatuses[cellId]) {
                delete this.cellStatuses[cellId];
                this.persistCellStatuses();
            }

        } catch (error) {
            console.error('Ошибка:', error);
            alert('Ошибка при удалении ячейки: ' + error.message);
        }
    },

    deleteNotebook(buttonElement) {
        const form = buttonElement.closest('form');

        if (!form) {
            return;
        }

        if (confirm('Удалить ноутбук?')) {
            form.submit();
        }
    },

    initializeCells() {
        if (!this.notebookElement) {
            return;
        }

        const cells = this.notebookElement.querySelectorAll('[data-cell-id]');
        cells.forEach(cell => this.initializeCell(cell));
    },

    initializeCell(cellElement) {
        if (!cellElement) {
            return;
        }

        if (cellElement.dataset.cellType === 'latex') {
            this.refreshLatexDisplay(cellElement);
            this.setLatexEditingState(cellElement, false);
        }
    },

    startLatexEdit(cellElement) {
        if (!cellElement) {
            return;
        }

        const textarea = cellElement.querySelector('[data-latex-textarea]');
        if (!textarea) {
            return;
        }

        this.setLatexEditingState(cellElement, true);
        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    },

    async saveLatexCell(cellId, cellElement) {
        const notebookId = this.config?.notebookId;
        const textarea = cellElement?.querySelector('[data-latex-textarea]');
        const display = cellElement?.querySelector('[data-latex-display]');

        if (!textarea || !display || !this.notebookElement) {
            return;
        }

        const newContent = textarea.value;
        const saveOutputUrl = this.buildCellUrl(this.saveOutputUrlTemplate, cellId);

        try {
            const result = await NotebookUtils.saveCellOutput(
                notebookId,
                cellId,
                newContent,
                '',
                this.config.csrfToken,
                saveOutputUrl
            );

            if (result?.ok === false) {
                const message = result.error instanceof Error ? result.error.message : 'Не удалось сохранить ячейку';
                throw new Error(message);
            }

            this.refreshLatexDisplay(cellElement, newContent);
            this.setLatexEditingState(cellElement, false);

        } catch (error) {
            console.error('Ошибка сохранения LaTeX:', error);
            alert('Ошибка при сохранении ячейки: ' + (error.message || error));
        }
    },

    cancelLatexEdit(cellElement) {
        if (!cellElement) {
            return;
        }

        const display = cellElement.querySelector('[data-latex-display]');
        const textarea = cellElement.querySelector('[data-latex-textarea]');

        if (!display || !textarea) {
            return;
        }

        const original = display.dataset.content ?? '';
        textarea.value = original;
        this.setLatexEditingState(cellElement, false);
        NotebookUtils.renderLatex(original, display);
    },

    refreshLatexDisplay(cellElement, newContent) {
        const display = cellElement?.querySelector('[data-latex-display]');
        const textarea = cellElement?.querySelector('[data-latex-textarea]');

        if (!display || !textarea) {
            return;
        }

        const content = typeof newContent === 'string' ? newContent : textarea.value;
        display.dataset.content = content;
        NotebookUtils.renderLatex(content, display);
    },

    setLatexEditingState(cellElement, isEditing) {
        const editor = cellElement?.querySelector('[data-latex-editor]');
        const display = cellElement?.querySelector('[data-latex-display]');
        const textarea = cellElement?.querySelector('[data-latex-textarea]');
        const editButton = cellElement?.querySelector('[data-action="edit-latex"]');

        if (!editor || !display || !textarea || !editButton) {
            return;
        }

        if (isEditing) {
            editor.hidden = false;
            textarea.disabled = false;
            display.hidden = true;
            editButton.hidden = true;
        } else {
            editor.hidden = true;
            textarea.disabled = true;
            display.hidden = false;
            editButton.hidden = false;
        }
    }
};
