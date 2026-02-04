const MAX_FILES_DISPLAY = 200;

const notebookDetail = {
    config: null,
    notebookElement: null,
    sessionId: null,
    sessionPromise: null,
    cellStatuses: {},
    cellQueue: [],
    currentRun: null,
    cellOutputSnapshots: {},
    storageEnabled: undefined,
    inactivityTimers: {
        prompt: null,
        ban: null,
    },
    inactivityOverlay: null,
    lastActivityTs: null,
    filesRequestId: 0,
    sessionState: 'idle',
    sessionStatusLabels: {
        idle: 'Сессия не создана',
        creating: 'Создание сессии...',
        ready: 'Сессия создана',
        restarting: 'Перезапуск сессии...',
        stopping: 'Остановка сессии...',
        error: 'Ошибка сессии. Создайте новую.',
    },
    sessionStatusElement: null,
    sessionButtons: {},
    clipboardCellId: null,
    clipboardIndicator: null,

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
        this.filesLoadedFor = null;
        this.filesRequestId += 1;
        this.resetFilesPanelMarkup();
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
                    const nextState = (value === 'running' || value === 'queued') ? 'idle' : value;
                    normalized[cellId] = { state: nextState };
                } else if (value && typeof value === 'object' && value.state) {
                    let nextState = value.state;
                    let nextMeta = value.meta && typeof value.meta === 'object' ? value.meta : null;
                    if (nextState === 'running' || nextState === 'queued') {
                        nextState = 'idle';
                        nextMeta = null;
                    }
                    normalized[cellId] = {
                        state: nextState,
                        meta: nextMeta,
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
            case 'queued': {
                const ahead = typeof meta?.queueAhead === 'number' ? meta.queueAhead : null;
                if (ahead && ahead > 0) {
                    return `Ожидает запуска (перед ней ${ahead})`;
                }
                return 'Ожидает запуска (следующая)';
            }
            case 'error':
                return 'Ошибка';
            case 'cancelled':
                return 'Отменено';
            case 'reset':
                return 'Нужен повторный запуск';
            case 'input':
                return 'Ожидает ввода';
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
        const requiresCancel = status === 'running' || status === 'queued';
        this.updateRunButtonState(cellId, requiresCancel ? 'cancel' : 'run');
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
            const finalStatus = status === 'idle' ? 'idle' : status;
            this.updateCellStatusElement(cellId, finalStatus, null);
            const requiresCancel = finalStatus === 'running' || finalStatus === 'queued';
            this.updateRunButtonState(cellId, requiresCancel ? 'cancel' : 'run');
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
            const requiresCancel = status === 'running' || status === 'queued';
            this.updateRunButtonState(cellId, requiresCancel ? 'cancel' : 'run');
        });
    },

    updateRunButtonState(cellId, mode) {
        const cellElement = document.querySelector(`[data-cell-id="${cellId}"]`);
        if (!cellElement) {
            return;
        }
        const button = cellElement.querySelector('[data-action="run-cell"]');
        if (!button) {
            return;
        }
        if (mode === 'cancel') {
            button.textContent = 'Отменить';
            button.dataset.mode = 'cancel';
        } else {
            button.textContent = 'Запустить';
            delete button.dataset.mode;
        }
    },

    rememberOutputSnapshot(cellId, html) {
        if (!cellId) {
            return;
        }
        this.cellOutputSnapshots[cellId] = html ?? '';
    },

    getOutputSnapshot(cellId) {
        if (!cellId) {
            return '';
        }
        return this.cellOutputSnapshots[cellId] || '';
    },

    insertStdinInput(outputElement, promptText) {
        if (!outputElement) {
            return null;
        }
        let pre = outputElement.querySelector('.output-text pre');
        if (!pre) {
            const container = document.createElement('div');
            container.className = 'output-text';
            pre = document.createElement('pre');
            container.appendChild(pre);
            outputElement.appendChild(container);
        }
        // Keep only one active inline stdin control to avoid stale inputs in the DOM.
        pre.querySelectorAll('.stdin-inline').forEach((node) => node.remove());
        const wrapper = document.createElement('span');
        wrapper.className = 'stdin-inline';
        const input = document.createElement('input');
        input.type = 'text';
        input.autocomplete = 'off';
        input.spellcheck = false;
        input.className = 'stdin-input';
        input.style.font = 'inherit';
        input.style.background = 'transparent';
        input.style.border = 'none';
        input.style.outline = 'none';
        input.style.color = 'inherit';
        if (promptText) {
            const promptLen = Math.max(0, String(promptText).length);
            input.style.width = `calc(100% - ${promptLen}ch)`;
            input.style.minWidth = '8ch';
        } else {
            input.style.width = '100%';
        }
        wrapper.appendChild(input);
        pre.appendChild(wrapper);
        input.focus();
        return input;
    },

    async handleStdinLoop({
        cellId,
        cellNumericId,
        outputElement,
        sessionId,
        saveOutputUrl,
        code,
        startedAt,
        job,
        data,
    }) {
        return new Promise((resolve, reject) => {
            const attach = (payload) => {
                const input = this.insertStdinInput(outputElement, payload?.prompt);
                if (!input) {
                    reject(new Error('Не удалось создать поле ввода'));
                    return;
                }
                const onKey = async (event) => {
                    if (event.key !== 'Enter') {
                        return;
                    }
                    event.preventDefault();
                    input.removeEventListener('keydown', onKey);
                    input.disabled = true;
                    try {
                        const response = await fetch(this.runCellUrl, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': this.config.csrfToken
                            },
                            body: JSON.stringify({
                                session_id: sessionId,
                                cell_id: cellNumericId,
                                run_id: payload?.run_id,
                                stdin: `${input.value}\n`
                            }),
                            signal: job.controller?.signal
                        });
                        const nextData = await response.json();
                        if (!response.ok) {
                            const message = nextData?.detail || nextData?.error || 'Не удалось выполнить ячейку';
                            const error = new Error(message);
                            error.status = response.status;
                            throw error;
                        }

                        const hasOutput = Boolean(nextData.stdout || nextData.stderr || nextData.error);
                        let formatted = '';
                        if (nextData.status === 'input_required' && !hasOutput) {
                            outputElement.innerHTML = '';
                        } else {
                            formatted = NotebookUtils.formatCellRunResult(nextData);
                            outputElement.innerHTML = formatted;
                        }
                        outputElement.className = nextData.error ? 'output error' : 'output success';
                        this.renderArtifacts(cellId, []);

                        if (nextData.status === 'input_required') {
                            outputElement.className = 'output running';
                            this.setCellStatus(cellId, 'input');
                            attach(nextData);
                            return;
                        }

                        const finalStatus = nextData.error ? 'error' : 'success';
                        const durationMs = Math.max(
                            0,
                            (typeof performance !== 'undefined' ? performance.now() : Date.now()) - startedAt,
                        );
                        const meta = finalStatus === 'success' ? { durationMs } : null;
                        this.setCellStatus(cellId, finalStatus, meta);
                        this.rememberOutputSnapshot(cellId, formatted);
                        await this.saveCellState(cellId, code, formatted, saveOutputUrl);
                        resolve();
                    } catch (error) {
                        // Отображаем ошибку пользователю
                        const message = (error && error.message) ? error.message : 'Произошла ошибка при отправке ввода.';
                        outputElement.className = 'output error';
                        outputElement.textContent = `Ошибка ввода: ${message}`;
                        this.setCellStatus(cellId, 'error');
                        this.rememberOutputSnapshot(cellId, outputElement.innerHTML);
                        reject(error);
                    }
                };
                input.addEventListener('keydown', onKey);
            };
            attach(data);
        });
    },

    captureInitialOutputs() {
        const outputs = document.querySelectorAll('.cell .output');
        outputs.forEach((outputElement) => {
            const cellElement = outputElement.closest('[data-cell-id]');
            const cellId = cellElement?.dataset.cellId;
            if (!cellId) {
                return;
            }
            this.rememberOutputSnapshot(cellId, outputElement.innerHTML);
        });
    },

    isCellQueued(cellId) {
        return this.cellQueue.some((job) => job.cellId === cellId);
    },

    cancelQueuedCell(cellId) {
        const before = this.cellQueue.length;
        this.cellQueue = this.cellQueue.filter((job) => job.cellId !== cellId);
        if (this.cellQueue.length === before) {
            return false;
        }
        this.setCellStatus(cellId, 'idle');
        this.updateQueueStatuses();
        return true;
    },

    updateQueueStatuses() {
        this.cellQueue.forEach((job, index) => {
            this.setCellStatus(job.cellId, 'queued', {
                queuePosition: index + 1,
                queueAhead: index,
            });
        });
        Object.entries({ ...this.cellStatuses }).forEach(([cellId, record]) => {
            if (record?.state === 'queued') {
                const stillQueued = this.cellQueue.some((job) => job.cellId === cellId);
                const running = this.currentRun?.cellId === cellId;
                if (!stillQueued && !running) {
                    this.setCellStatus(cellId, 'idle');
                }
            }
        });
    },

    enqueueCellRun(cellId) {
        this.cellQueue.push({ cellId, enqueuedAt: Date.now() });
        this.updateQueueStatuses();
        this.processQueue();
    },

    processQueue() {
        if (this.currentRun || this.cellQueue.length === 0) {
            return;
        }
        const nextJob = this.cellQueue.shift();
        if (!nextJob) {
            return;
        }
        this.updateQueueStatuses();
        this.startQueueJob(nextJob);
    },

    startQueueJob(job) {
        const controller = typeof AbortController === 'function' ? new AbortController() : null;
        job.controller = controller;
        job.cancelled = false;
        this.currentRun = job;
        this.executeQueueJob(job).finally(() => {
            const cellId = job.cellId;
            if (this.currentRun && this.currentRun.cellId === cellId) {
                this.currentRun = null;
            }
            this.updateRunButtonState(cellId, 'run');
            this.updateQueueStatuses();
            this.processQueue();
            this.refreshSessionFiles();
        });
    },

    cancelCurrentRun(reason = 'user') {
        if (!this.currentRun) {
            return;
        }
        this.currentRun.cancelled = reason;
        if (this.currentRun.controller) {
            this.currentRun.controller.abort();
        }
    },

    abortAllRuns(reason = 'reset') {
        if (this.currentRun) {
            this.cancelCurrentRun(reason);
        }
        if (this.cellQueue.length > 0) {
            this.cellQueue = [];
            this.updateQueueStatuses();
        }
    },

    async executeQueueJob(job) {
        const cellId = job.cellId;
        const cellElement = document.querySelector(`[data-cell-id="${cellId}"]`);
        if (!cellElement) {
            return;
        }
        const textarea = cellElement.querySelector('textarea');
        const outputElement = document.getElementById(`output-${cellId}`);
        const saveOutputUrl = this.buildCellUrl(this.saveOutputUrlTemplate, cellId);
        const runCellUrl = this.runCellUrl;

        if (!textarea || !outputElement || !runCellUrl) {
            this.setCellStatus(cellId, 'error');
            return;
        }

        const cellNumericId = Number(cellId);
        if (Number.isNaN(cellNumericId)) {
            alert('Некорректный идентификатор ячейки');
            this.setCellStatus(cellId, 'error');
            return;
        }

        const sessionId = await this.ensureSession();

        if (!sessionId) {
            alert('Сначала создайте сессию.');
            this.updateSessionStatus('idle', 'Сессия не создана. Создайте новую.');
            this.setCellStatus(cellId, 'error');
            return;
        }

        const code = textarea.value;
        this.markActivity();
        await this.saveCellState(cellId, code, outputElement.innerHTML, saveOutputUrl);

        this.renderArtifacts(cellId, []);
        job.previousOutputHtml = outputElement.innerHTML || this.getOutputSnapshot(cellId);
        outputElement.innerHTML = '<div class="output-loading">Выполнение...</div>';
        outputElement.className = 'output running';
        this.setCellStatus(cellId, 'running');
        this.updateRunButtonState(cellId, 'cancel');

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
                }),
                signal: job.controller?.signal
            });

            const data = await response.json();

            if (!response.ok) {
                const message = data?.detail || data?.error || 'Не удалось выполнить ячейку';
                const error = new Error(message);
                error.status = response.status;
                throw error;
            }

            const hasAnyOutput = Boolean(data.stdout || data.stderr || data.error);
            let formattedOutput = '';
            if (data.status === 'input_required' && !hasAnyOutput) {
                outputElement.innerHTML = '';
            } else {
                formattedOutput = NotebookUtils.formatCellRunResult(data);
                outputElement.innerHTML = formattedOutput;
            }
            outputElement.className = data.error ? 'output error' : 'output success';
            this.renderArtifacts(cellId, []);
            if (data.status === 'input_required') {
                outputElement.className = 'output running';
                this.setCellStatus(cellId, 'input');
                await this.handleStdinLoop({
                    cellId,
                    cellNumericId,
                    outputElement,
                    sessionId,
                    saveOutputUrl,
                    code,
                    startedAt,
                    job,
                    data,
                });
                return;
            }
            const finalStatus = data.error ? 'error' : 'success';
            const durationMs = Math.max(
                0,
                (typeof performance !== 'undefined' ? performance.now() : Date.now()) - startedAt,
            );
            const meta = finalStatus === 'success' ? { durationMs } : null;
            this.setCellStatus(cellId, finalStatus, meta);
            this.rememberOutputSnapshot(cellId, formattedOutput);
            await this.saveCellState(cellId, code, formattedOutput, saveOutputUrl);
        } catch (error) {
            if (error?.status === 400 && /Сессия не создана/i.test(error.message || '')) {
                this.handleSessionLost('Сессия не создана. Создайте новую.');
            }
            if (job.cancelled) {
                const reason = job.cancelled === 'reset'
                    ? 'Выполнение остановлено из-за перезапуска сессии.'
                    : 'Выполнение отменено пользователем.';
                if (job.cancelled === 'reset') {
                    const fallback = job.previousOutputHtml || this.getOutputSnapshot(cellId) || '<div class="output-empty">Нет вывода</div>';
                    outputElement.innerHTML = fallback;
                    outputElement.className = 'output';
                    this.renderArtifacts(cellId, []);
                    this.setCellStatus(cellId, 'reset');
                } else {
                    const note = `<div class="output-error"><strong>Отмена:</strong> ${NotebookUtils.escapeHtml(reason)}</div>`;
                    outputElement.innerHTML = note;
                    outputElement.className = 'output error';
                    this.renderArtifacts(cellId, []);
                    this.setCellStatus(cellId, 'cancelled');
                    this.rememberOutputSnapshot(cellId, note);
                    await this.saveCellState(cellId, code, note, saveOutputUrl);
                }
                return;
            }
            console.error('Ошибка выполнения ячейки:', error);
            const message = error?.message || 'Не удалось выполнить ячейку';
            const errorHtml = `<div class="output-error">${NotebookUtils.escapeHtml(message)}</div>`;
            outputElement.innerHTML = errorHtml;
            outputElement.className = 'output error';
            this.renderArtifacts(cellId, []);
            this.setCellStatus(cellId, 'error');
            this.rememberOutputSnapshot(cellId, errorHtml);
            await this.saveCellState(cellId, code, errorHtml, saveOutputUrl);
        }
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
        this.copyCellUrlTemplate = this.notebookElement?.dataset.copyCellUrlTemplate || '';
        this.moveCellUrlTemplate = this.notebookElement?.dataset.moveCellUrlTemplate || '';
        this.runCellUrl = this.sanitizeUrl(config.runCellUrl) || this.sanitizeUrl(this.notebookElement?.dataset.runCellUrl);
        this.sessionCreateUrl = this.sanitizeUrl(config.sessionCreateUrl) || this.sanitizeUrl(this.notebookElement?.dataset.sessionCreateUrl);
        this.sessionResetUrl = this.sanitizeUrl(config.sessionResetUrl) || this.sanitizeUrl(this.notebookElement?.dataset.sessionResetUrl);
        this.sessionFilesUrl = this.sanitizeUrl(config.sessionFilesUrl) || this.sanitizeUrl(this.notebookElement?.dataset.sessionFilesUrl);
        this.sessionFileUploadUrl = this.sanitizeUrl(config.sessionFileUploadUrl) || this.sanitizeUrl(this.notebookElement?.dataset.sessionFileUploadUrl);
        this.sessionFileDownloadUrl = this.sanitizeUrl(config.sessionFileDownloadUrl) || this.sanitizeUrl(this.notebookElement?.dataset.sessionFileDownloadUrl);
        this.sessionStopUrl = this.sanitizeUrl(config.sessionStopUrl) || this.sanitizeUrl(this.notebookElement?.dataset.sessionStopUrl);
        this.sessionStatusElement = this.notebookElement?.querySelector('[data-session-status]') || null;
        this.sessionButtons = {
            create: this.notebookElement?.querySelector('[data-action="create-session"]') || null,
            reset: this.notebookElement?.querySelector('[data-action="reset-session"]') || null,
            stop: this.notebookElement?.querySelector('[data-action="stop-session"]') || null,
        };
        this.clipboardCellId = null;
        this.clipboardIndicator = this.notebookElement?.querySelector('[data-clipboard-indicator]') || null;
        this.filesPanel = document.querySelector('[data-files-panel]');
        this.filesList = this.filesPanel?.querySelector('[data-files-list]');
        this.filesLoadedFor = null;
        this.filesRequestId = 0;
        this.initialFilesLoaded = false;
        this.cellStatuses = this.loadCellStatuses();
        this.saveTextCellUrlTemplate = this.notebookElement?.dataset.saveTextCellUrlTemplate || '';
        this.bindEvents();
        this.initImportExport();
        this.initializeCells();
        this.updatePasteButtonsState();
        this.updateClipboardIndicator();
        this.updateClipboardHighlights();
        this.captureInitialOutputs();
        this.applyStatusesToExistingCells();
        this.updateQueueStatuses();
        this.initActivityTracking();
        const restored = this.getStoredSessionId();
        if (restored) {
            this.sessionId = restored;
            this.updateSessionStatus('ready');
            this.refreshSessionFiles();
        } else {
            this.updateSessionStatus('idle');
        }
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

        if (this.filesPanel) {
            this.filesPanel.addEventListener('change', (event) => {
                const target = event.target;
                if (target && target.matches('[data-upload-input]')) {
                    this.handleUploadInputChange(event);
                }
            });
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
        else if (action === 'create-text-cell') {
            this.createTextCell();
        }
        else if (action === 'run-cell' && cellId) {
            this.runCell(cellId);
        }
        else if (action === 'delete-cell' && cellId) {
            this.deleteCell(cellId, cellElement);
        }
        else if (action === 'copy-cell' && cellId) {
            this.saveCellToClipboard(cellId);
        }
        else if (action === 'duplicate-cell' && cellId) {
            this.duplicateCell(cellId, cellElement);
        }
        else if (action === 'paste-cell-before' && cellId) {
            this.pasteCellRelative(cellElement, 'before');
        }
        else if (action === 'paste-cell-after' && cellId) {
            this.pasteCellRelative(cellElement, 'after');
        }
        else if (action === 'paste-at-end') {
            this.pasteCellAtEnd();
        }
        else if (action === 'move-up' && cellId) {
            this.handleMoveCell(cellElement, -1);
        }
        else if (action === 'move-down' && cellId) {
            this.handleMoveCell(cellElement, 1);
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
        else if (action === 'create-session') {
            this.requestSessionCreation();
        }
        else if (action === 'reset-session') {
            this.confirmAndResetSession();
        }
        else if (action === 'stop-session') {
            this.confirmAndStopSession();
        }
        else if (action === 'refresh-files') {
            this.refreshSessionFiles();
        }
        else if (action === 'upload-file') {
            this.triggerFileUploadSelect();
        }
        else if (action === 'export-notebook') {
            this.exportNotebook();
        }
        else if (action === 'import-notebook') {
            this.triggerImportFileSelect();
        }
    },

    saveCellToClipboard(cellId) {
        if (!cellId) {
            return;
        }
        this.setClipboardCell(cellId);
    },

    setClipboardCell(cellId) {
        this.clipboardCellId = cellId || null;
        this.updateClipboardIndicator();
        this.updateClipboardHighlights();
        this.updatePasteButtonsState();
    },

    updateClipboardIndicator() {
        if (!this.clipboardIndicator) {
            return;
        }
        if (this.clipboardCellId) {
            const cellNumber = this.getCellNumberById(this.clipboardCellId);
            const suffix = cellNumber ? `ячейка ${cellNumber}` : `ячейка #${this.clipboardCellId}`;
            this.clipboardIndicator.textContent = `В буфере: ${suffix}`;
            this.clipboardIndicator.dataset.state = 'active';
        } else {
            this.clipboardIndicator.textContent = 'Буфер пуст';
            this.clipboardIndicator.dataset.state = 'empty';
        }
    },

    getCellNumberById(cellId) {
        if (!cellId) {
            return null;
        }
        const element = this.notebookElement?.querySelector(`[data-cell-id="${cellId}"]`);
        if (!element) {
            return null;
        }
        const index = this.getCellIndex(element);
        return index === -1 ? null : index + 1;
    },

    updateClipboardHighlights() {
        if (!this.notebookElement) {
            return;
        }
        const cells = this.notebookElement.querySelectorAll('[data-cell-id]');
        cells.forEach((element) => {
            if (element.dataset.cellId === this.clipboardCellId) {
                element.classList.add('clipboard-highlight');
                element.dataset.clipboard = 'true';
            } else {
                element.classList.remove('clipboard-highlight');
                delete element.dataset.clipboard;
            }
        });
    },

    updatePasteButtonsState() {
        if (!this.notebookElement) {
            return;
        }
        const hasClipboard = Boolean(this.clipboardCellId);
        const buttons = this.notebookElement.querySelectorAll('[data-paste-button]');
        buttons.forEach((button) => {
            if (hasClipboard) {
                button.removeAttribute('disabled');
            } else {
                button.setAttribute('disabled', 'disabled');
            }
        });
    },

    clearClipboardIfMatches(cellId) {
        if (this.clipboardCellId === cellId) {
            this.setClipboardCell(null);
        } else {
            this.updateClipboardHighlights();
        }
    },

    async ensureSession() {
        if (this.sessionId) {
            return this.sessionId;
        }
        const stored = this.getStoredSessionId();
        if (stored) {
            this.sessionId = stored;
            this.updateSessionStatus('ready');
            if (this.filesLoadedFor !== stored) {
                this.refreshSessionFiles();
            }
            return stored;
        }
        return null;
    },

    async createSession() {
        if (this.sessionPromise) {
            return this.sessionPromise;
        }
        const promise = (async () => {
            if (!this.sessionCreateUrl) {
                throw new Error('URL создания сессии недоступен');
            }
            this.updateSessionStatus('creating');
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
                this.updateSessionStatus('error', message);
                throw new Error(message);
            }
            this.sessionId = data.session_id;
            this.storeSessionId(this.sessionId);
            this.updateSessionStatus('ready');
            this.refreshSessionFiles();
            return this.sessionId;
        })();
        this.sessionPromise = promise;
        try {
            return await promise;
        } finally {
            if (this.sessionPromise === promise) {
                this.sessionPromise = null;
            }
        }
    },

    async requestSessionCreation() {
        if (this.sessionId) {
            alert('Сессия уже создана.');
            return;
        }
        try {
            await this.createSession();
        } catch (error) {
            console.error('Не удалось создать сессию:', error);
            const message = error?.message || 'Не удалось создать сессию';
            alert(message);
        }
    },

    updateSessionStatus(state, customMessage) {
        this.sessionState = state;
        const label = customMessage || this.sessionStatusLabels[state] || this.sessionStatusLabels.idle;
        if (this.sessionStatusElement) {
            this.sessionStatusElement.textContent = label;
            this.sessionStatusElement.dataset.state = state;
        }
        const hasSession = state === 'ready';
        const busy = state === 'creating' || state === 'restarting' || state === 'stopping';
        const disableCreate = busy || hasSession;
        const disableManage = busy || !hasSession;
        if (this.sessionButtons?.create) {
            this.sessionButtons.create.disabled = disableCreate;
        }
        if (this.sessionButtons?.reset) {
            this.sessionButtons.reset.disabled = disableManage;
        }
        if (this.sessionButtons?.stop) {
            this.sessionButtons.stop.disabled = disableManage;
        }
    },

    handleSessionLost(message) {
        this.sessionId = null;
        this.clearStoredSessionId();
        this.updateSessionStatus('idle', message);
        this.resetAllCellStatuses('reset');
    },

    async resetSession(options = {}) {
        const { silent = false, reason = 'user' } = options;
        const sessionId = await this.ensureSession();
        if (!sessionId) {
            alert('Сначала создайте сессию.');
            return;
        }
        if (!this.sessionResetUrl) {
            alert('URL сброса сессии недоступен');
            return;
        }
        try {
            if (reason !== 'ban') {
                this.markActivity();
            }
            this.abortAllRuns('reset');
            this.updateSessionStatus('restarting');
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
                const message = data?.detail || data?.message || 'Не удалось перезапустить сессию';
                const error = new Error(message);
                error.status = response.status;
                throw error;
            }
            this.clearStoredSessionId();
            this.sessionId = data.session_id;
            this.storeSessionId(this.sessionId);
            this.resetFilesPanelMarkup();
            this.refreshSessionFiles();
            this.clearOutputsAfterReset();
            this.resetAllCellStatuses('reset');
            this.updateSessionStatus('ready');
            if (!silent && reason !== 'ban') {
                alert('Сессия перезапущена. Все переменные очищены.');
            }
        } catch (error) {
            console.error('Ошибка сброса сессии:', error);
            if (error?.status === 404) {
                this.handleSessionLost('Сессия не найдена. Создайте новую.');
            } else if (this.sessionId) {
                this.updateSessionStatus('ready');
            } else {
                this.updateSessionStatus('idle');
            }
            if (!silent) {
                alert('Не удалось перезапустить сессию: ' + (error?.message || error));
            }
        }
    },

    confirmAndResetSession() {
        const ok = window.confirm('Перезапустить сессию? Все переменные будут очищены.');
        if (!ok) {
            return;
        }
        this.resetSession();
    },

    async stopSession() {
        const sessionId = await this.ensureSession();
        if (!sessionId) {
            alert('Сессия не создана.');
            return;
        }
        if (!this.sessionStopUrl) {
            alert('URL остановки сессии недоступен');
            return;
        }
        try {
            this.updateSessionStatus('stopping');
            const response = await fetch(this.sessionStopUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken,
                },
                body: JSON.stringify({ session_id: sessionId }),
            });
            const data = await response.json();
            if (!response.ok) {
                const message = data?.detail || data?.message || 'Не удалось остановить сессию';
                const error = new Error(message);
                error.status = response.status;
                throw error;
            }
            this.handleSessionLost('Сессия остановлена. Создайте новую для продолжения работы.');
        } catch (error) {
            console.error('Не удалось остановить сессию:', error);
            if (error?.status === 404) {
                this.handleSessionLost('Сессия не найдена. Создайте новую.');
            } else {
                if (this.sessionId) {
                    this.updateSessionStatus('ready');
                } else {
                    this.updateSessionStatus('idle');
                }
                alert('Не удалось остановить сессию: ' + (error?.message || error));
            }
        }
    },

    confirmAndStopSession() {
        const hasSession = Boolean(this.sessionId || this.getStoredSessionId());
        if (!hasSession) {
            alert('Сессия не создана.');
            return;
        }
        const ok = window.confirm('Остановить текущую сессию? Все переменные и файлы будут удалены.');
        if (!ok) {
            return;
        }
        this.stopSession();
    },

    clearOutputsAfterReset() {
        const outputs = document.querySelectorAll('.cell .output');
        outputs.forEach((outputElement) => {
            const cellElement = outputElement.closest('[data-cell-id]');
            const cellId = cellElement?.dataset.cellId;
            const previousWrapper = outputElement.querySelector('.output-previous');
            const snapshot = cellId ? this.getOutputSnapshot(cellId) : '';
            const previousHtml = snapshot || previousWrapper?.innerHTML || outputElement.innerHTML || '<div class="output-empty">Нет вывода</div>';
            outputElement.innerHTML = `
                <div class="output-reset-note">Нужен повторный запуск. Ниже показан вывод предыдущей сессии.</div>
                <div class="output-previous">${previousHtml}</div>
            `;
            outputElement.className = 'output reset stale';
            const hasStatus = cellElement?.querySelector('[data-cell-status]');
            if (cellId && hasStatus) {
                this.setCellStatus(cellId, 'reset');
            }
        });
    },

    getCellsContainer() {
        return document.getElementById('cells-container');
    },

    getCellIndex(cellElement) {
        const container = this.getCellsContainer();
        if (!container || !cellElement) {
            return -1;
        }
        return Array.from(container.children).indexOf(cellElement);
    },

    insertCellHtmlAt(container, html, targetPosition) {
        if (!container || typeof html !== 'string') {
            return null;
        }
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html.trim();
        const newCell = wrapper.firstElementChild;
        if (!newCell) {
            return null;
        }
        const beforeElement = container.children[targetPosition] || null;
        container.insertBefore(newCell, beforeElement);
        return newCell;
    },

    updateCellTitles() {
        const container = this.getCellsContainer();
        if (!container) {
            return;
        }
        Array.from(container.children).forEach((cellElement, index) => {
            const titleElement = cellElement.querySelector('.cell-title');
            if (titleElement) {
                titleElement.textContent = `Ячейка ${index + 1}`;
            }
            cellElement.dataset.cellOrder = index;
        });
        this.updateClipboardHighlights();
    },

    applyCellOrder(order) {
        const container = this.getCellsContainer();
        if (!container || !Array.isArray(order)) {
            return;
        }
        const lookup = new Map();
        Array.from(container.children).forEach((child) => {
            const id = child?.dataset?.cellId;
            if (id) {
                lookup.set(id, child);
            }
        });
        const fragment = document.createDocumentFragment();
        order.forEach((item) => {
            const id = item?.id?.toString();
            if (!id) {
                return;
            }
            const element = lookup.get(id);
            if (element) {
                fragment.appendChild(element);
                lookup.delete(id);
            }
        });
        container.appendChild(fragment);
        this.updateCellTitles();
    },

    handleMoveCell(cellElement, offset) {
        if (!cellElement) {
            return;
        }
        const currentIndex = this.getCellIndex(cellElement);
        if (currentIndex === -1) {
            return;
        }
        const targetIndex = currentIndex + offset;
        const container = this.getCellsContainer();
        if (!container || targetIndex < 0 || targetIndex >= container.children.length) {
            return;
        }
        const cellId = cellElement.dataset?.cellId;
        if (!cellId) {
            return;
        }
        this.moveCell(cellId, targetIndex, cellElement);
    },

    async moveCell(cellId, targetPosition, cellElement) {
        try {
            const moveUrl = this.buildCellUrl(this.moveCellUrlTemplate, cellId);
            if (!moveUrl) {
                throw new Error('URL перемещения ячейки недоступен');
            }
            const response = await fetch(moveUrl, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken,
                },
                body: JSON.stringify({ target_position: targetPosition }),
            });
            const data = await response.json();
            if (!response.ok || data?.status !== 'success') {
                const message = data?.message || `HTTP error ${response.status}`;
                throw new Error(message);
            }
            if (Array.isArray(data?.order)) {
                this.applyCellOrder(data.order);
            } else {
                const container = this.getCellsContainer();
                const element = cellElement || document.querySelector(`[data-cell-id="${cellId}"]`);
                if (container && element) {
                    const before = container.children[targetPosition] || null;
                    container.insertBefore(element, before);
                    this.updateCellTitles();
                }
            }
        } catch (error) {
            console.error('Ошибка перемещения ячейки:', error);
            alert('Не удалось переместить ячейку: ' + (error.message || error));
        }
    },

    async duplicateCell(cellId, cellElement) {
        const index = this.getCellIndex(cellElement);
        if (index === -1) {
            return;
        }
        await this.copyCellFromSource(cellId, index + 1, 'дублировать ячейку');
    },

    async pasteCellRelative(cellElement, direction) {
        if (!this.clipboardCellId) {
            alert('Сначала скопируйте ячейку.');
            return;
        }
        const index = this.getCellIndex(cellElement);
        if (index === -1) {
            return;
        }
        const offset = direction === 'before' ? 0 : 1;
        await this.copyCellFromSource(this.clipboardCellId, index + offset, 'вставить ячейку');
    },

    async pasteCellAtEnd() {
        if (!this.clipboardCellId) {
            alert('Сначала скопируйте ячейку.');
            return;
        }
        const container = this.getCellsContainer();
        if (!container) {
            return;
        }
        await this.copyCellFromSource(this.clipboardCellId, container.children.length, 'вставить ячейку');
    },

    async copyCellFromSource(sourceCellId, targetPosition, actionLabel = 'создать копию ячейки') {
        try {
            const copyUrl = this.buildCellUrl(this.copyCellUrlTemplate, sourceCellId);
            if (!copyUrl) {
                throw new Error('URL копирования ячейки недоступен');
            }
            const headers = {
                'X-CSRFToken': this.config.csrfToken,
            };
            let body = null;
            if (typeof targetPosition === 'number' && Number.isFinite(targetPosition)) {
                headers['Content-Type'] = 'application/json';
                body = JSON.stringify({ target_position: targetPosition });
            }
            const response = await fetch(copyUrl, {
                method: 'POST',
                headers,
                body,
            });

            const data = await response.json();
            if (!response.ok || data?.status !== 'success') {
                const message = data?.message || `HTTP error ${response.status}`;
                throw new Error(message);
            }
            const container = this.getCellsContainer();
            if (!container) {
                throw new Error('Контейнер для ячеек не найден');
            }
            const insertionIndex = typeof targetPosition === 'number'
                ? targetPosition
                : (typeof data.execution_order === 'number' ? data.execution_order : container.children.length);
            const newCell = this.insertCellHtmlAt(container, data.html, insertionIndex);
            if (newCell) {
                this.initializeCell(newCell);
                const newCellId = newCell.dataset?.cellId;
                if (newCellId) {
                    const record = this.cellStatuses[newCellId];
                    const status = record?.state || 'idle';
                    this.updateCellStatusElement(newCellId, status, record?.meta);
                    const requiresCancel = status === 'running' || status === 'queued';
                    this.updateRunButtonState(newCellId, requiresCancel ? 'cancel' : 'run');
                    const newOutput = newCell.querySelector('.output');
                    if (newOutput) {
                        this.rememberOutputSnapshot(newCellId, newOutput.innerHTML);
                    }
                }
            }
            this.updateCellTitles();
            this.updatePasteButtonsState();
            return data;
        } catch (error) {
            console.error(`Ошибка при попытке ${actionLabel}:`, error);
            alert(`Не удалось ${actionLabel}: ` + (error.message || error));
            return null;
        }
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
                    const requiresCancel = status === 'running' || status === 'queued';
                    this.updateRunButtonState(newCellId, requiresCancel ? 'cancel' : 'run');
                    const newOutput = newCell.querySelector('.output');
                    if (newOutput) {
                        this.rememberOutputSnapshot(newCellId, newOutput.innerHTML);
                    }
                }
            }
            this.updateCellTitles();
            this.updatePasteButtonsState();

        } catch (error) {
            console.error('Ошибка:', error);
            alert('Ошибка при создании ячейки: ' + error.message);
        }
    },

    async createTextCell() {
        try {
            const createTextCellUrl = this.notebookElement?.dataset.createTextCellUrl;

            if (!createTextCellUrl) {
                throw new Error('URL создания текстовой ячейки недоступен');
            }

            const response = await fetch(createTextCellUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken
                }
            });

            if (!response.ok) {
                throw new Error('HTTP error ' + response.status);
            }

            const html = await response.text();
            const container = document.getElementById('cells-container');

            if (!container) {
                throw new Error('Контейнер для ячеек не найден');
            }

            container.insertAdjacentHTML('beforeend', html);
            const newCell = container.lastElementChild;
            if (newCell) {
                this.initializeCell(newCell);
                this.initTextCell(newCell);
            }

        } catch (error) {
            console.error('Ошибка:', error);
            alert('Ошибка при создании текстовой ячейки: ' + error.message);
        }
    },


    runCell(cellId) {
        if (!cellId) {
            return;
        }
        if (!this.runCellUrl) {
            alert('URL запуска ячейки недоступен');
            return;
        }
        if (this.currentRun?.cellId === cellId) {
            this.cancelCurrentRun('user');
            return;
        }
        if (this.cancelQueuedCell(cellId)) {
            return;
        }
        this.enqueueCellRun(cellId);
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

    async refreshSessionFiles() {
        if (!this.sessionFilesUrl) {
            return;
        }
        if (!this.sessionId) {
            if (this.filesList) {
                this.filesList.innerHTML = '<div class="files-empty">Создайте сессию, чтобы увидеть файлы.</div>';
            }
            return;
        }
        const requestId = ++this.filesRequestId;
        try {
            const url = `${this.sessionFilesUrl}?session_id=${encodeURIComponent(this.sessionId)}`;
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (response.status === 404) {
                const error = new Error('SESSION_NOT_FOUND');
                error.code = 'SESSION_NOT_FOUND';
                throw error;
            }
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            const data = await response.json();
            const files = Array.isArray(data?.files) ? data.files : [];
            if (requestId !== this.filesRequestId) {
                return;
            }
            this.renderSessionFiles(files);
        } catch (error) {
            if (error?.code === 'SESSION_NOT_FOUND') {
                this.handleSessionLost('Сессия не найдена. Создайте новую.');
                return;
            }
            console.error('Не удалось получить список файлов сессии:', error);
            if (this.filesList) {
                this.filesList.innerHTML = '<div class="files-error">Не удалось загрузить список файлов</div>';
            }
        }
    },

    async triggerFileUploadSelect() {
        if (!this.sessionFileUploadUrl) {
            alert('URL загрузки файлов недоступен');
            return;
        }
        let sessionId = await this.ensureSession();
        if (!sessionId) {
            const ok = window.confirm('Для загрузки файлов нужно создать сессию. Создать её сейчас?');
            if (!ok) {
                return;
            }
            try {
                sessionId = await this.createSession();
            } catch (error) {
                console.error('Не удалось создать сессию для загрузки файлов:', error);
                alert(error?.message || 'Не удалось создать сессию для загрузки.');
                return;
            }
        }
        const input = this.filesPanel?.querySelector('[data-upload-input]');
        if (!input) {
            alert('Поле выбора файла недоступно');
            return;
        }
        input.value = '';
        input.click();
    },

    async handleUploadInputChange(event) {
        const input = event?.target;
        if (!input || !input.files || input.files.length === 0) {
            return;
        }
        const files = Array.from(input.files);
        input.value = '';
        await this.uploadFiles(files);
    },

    async uploadFiles(files) {
        if (!files || files.length === 0) {
            return;
        }
        if (!this.sessionFileUploadUrl) {
            alert('URL загрузки файлов недоступен');
            return;
        }
        const sessionId = await this.ensureSession();
        if (!sessionId) {
            alert('Сначала создайте сессию.');
            return;
        }

        let uploadedCount = 0;
        const failed = [];
        for (const file of files) {
            if (!file) {
                continue;
            }
            const formData = new FormData();
            formData.append('session_id', sessionId);
            formData.append('file', file, file.name || 'uploaded.file');
            try {
                this.markActivity();
                const response = await fetch(this.sessionFileUploadUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.config.csrfToken
                    },
                    body: formData
                });
                let data = null;
                try {
                    data = await response.json();
                } catch (_error) {
                    data = null;
                }
                if (!response.ok) {
                    const message = data?.detail || data?.message || 'Не удалось загрузить файл';
                    const error = new Error(message);
                    error.status = response.status;
                    throw error;
                }
                uploadedCount += 1;
            } catch (error) {
                if (error?.status === 404) {
                    this.handleSessionLost('Сессия не найдена. Создайте новую.');
                }
                console.error('Не удалось загрузить файл:', error);
                const name = file?.name || 'файл';
                failed.push(name);
            }
        }

        await this.refreshSessionFiles();

        if (failed.length === 0) {
            alert(uploadedCount > 1 ? 'Файлы загружены.' : 'Файл загружен.');
        } else if (uploadedCount > 0) {
            alert(`Загружено файлов: ${uploadedCount}. Не удалось: ${failed.join(', ')}`);
        } else {
            alert('Не удалось загрузить выбранные файлы.');
        }
    },

    renderSessionFiles(files) {
        if (!this.filesList) {
            return;
        }
        if (!Array.isArray(files) || files.length === 0) {
            this.filesList.innerHTML = '<div class="files-empty">Файлы ещё не созданы</div>';
            this.filesLoadedFor = this.sessionId || null;
            return;
        }
        const sessionId = this.sessionId ? encodeURIComponent(this.sessionId) : '';
        const downloadBase = this.sessionFileDownloadUrl;
        const items = files.slice(0, MAX_FILES_DISPLAY).map((file) => {
            const safePath = NotebookUtils.escapeHtml(file.path || 'file');
            const sizeLabel = this.formatFileSize(file.size);
            const href = downloadBase && sessionId
                ? `${downloadBase}?session_id=${sessionId}&path=${encodeURIComponent(file.path)}`
                : '';
            const link = href
                ? `<a href="${href}" target="_blank" rel="noopener noreferrer">${safePath}</a>`
                : `<span>${safePath}</span>`;
            return `<div class="file-entry">
                ${link}
                <span class="file-meta">${sizeLabel}</span>
            </div>`;
        }).join('');
        this.filesList.innerHTML = items;
        this.filesLoadedFor = this.sessionId || null;
    },

    resetFilesPanelMarkup() {
        if (!this.filesPanel) {
            return;
        }
        this.filesPanel.innerHTML = `
            <div class="files-panel-header">
                <span>Файлы сессии</span>
                <div class="files-panel-actions">
                    <button type="button" data-action="refresh-files">Обновить</button>
                    <button type="button" data-action="upload-file">Загрузить файл</button>
                    <input type="file" data-upload-input multiple style="display: none;">
                </div>
            </div>
            <div class="files-panel-body" data-files-list>
                <div class="files-empty">Файлы ещё не созданы</div>
            </div>
        `;
        this.filesList = this.filesPanel.querySelector('[data-files-list]');
    },

    formatFileSize(bytes) {
        const value = Number(bytes);
        if (!Number.isFinite(value) || value < 0) {
            return '';
        }
        if (value >= 1024 * 1024) {
            return `${(value / (1024 * 1024)).toFixed(1)} МБ`;
        }
        if (value >= 1024) {
            return `${(value / 1024).toFixed(1)} КБ`;
        }
        return `${value} Б`;
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

            this.cancelQueuedCell(cellId);
            if (this.currentRun?.cellId === cellId) {
                this.cancelCurrentRun('user');
            }

            cellElement.remove();
            this.updateCellTitles();
            this.clearClipboardIfMatches(cellId);
            if (this.cellStatuses[cellId]) {
                delete this.cellStatuses[cellId];
                this.persistCellStatuses();
            }
            if (this.cellOutputSnapshots[cellId]) {
                delete this.cellOutputSnapshots[cellId];
            }
            this.refreshSessionFiles();
            this.updatePasteButtonsState();

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
        } else if (cellElement.dataset.cellType === 'text') {
            this.initTextCell(cellElement);
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
    },

    initTextCells() {
        if (!this.notebookElement) {
            return;
        }
        const containers = this.notebookElement.querySelectorAll('[data-text-container]');
        containers.forEach(container => this.initTextCell(container.closest('[data-cell-id]')));
    },

    initTextCell(cellElement) {
        if (!cellElement) {
            return;
        }
        const container = cellElement.querySelector('[data-text-container]');
        if (!container) {
            return;
        }

        const display = container.querySelector('[data-text-display]');
        const editor = container.querySelector('[data-text-editor]');
        const textarea = container.querySelector('[data-text-textarea]');
        const editBtn = container.querySelector('[data-action="edit-text"]');
        const saveBtn = container.querySelector('[data-action="save-text"]');
        const cancelBtn = container.querySelector('[data-action="cancel-text"]');

        if (!display || !editor || !textarea || !editBtn || !saveBtn || !cancelBtn) {
            return;
        }

    
        const rawContent = textarea.value || '';
        if (rawContent && display.innerHTML === rawContent) {
            const renderer = NotebookUtils.getMarkdownRenderer();
            display.innerHTML = renderer.render(rawContent);
        }

        let mde = null;

    
        const newEditBtn = editBtn.cloneNode(true);
        const newSaveBtn = saveBtn.cloneNode(true);
        const newCancelBtn = cancelBtn.cloneNode(true);
        editBtn.parentNode.replaceChild(newEditBtn, editBtn);
        saveBtn.parentNode.replaceChild(newSaveBtn, saveBtn);
        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);

        newEditBtn.addEventListener('click', () => {
            display.hidden = true;
            editor.hidden = false;

        
            if (!mde) {
                mde = new EasyMDE({
                    element: textarea,
                    autoDownloadFontAwesome: false,
                    spellChecker: false
                });
            }
            mde.codemirror.refresh();
        });

        newSaveBtn.addEventListener('click', async () => {
            const markdown = mde ? mde.value() : textarea.value;
            const cellId = cellElement.dataset.cellId;
            const saveUrl = this.buildCellUrl(this.saveTextCellUrlTemplate, cellId);

            if (!saveUrl) {
                alert('URL сохранения недоступен');
                return;
            }

            try {
                const response = await fetch(saveUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.config.csrfToken
                    },
                    body: JSON.stringify({ content: markdown })
                });

                if (!response.ok) {
                    throw new Error('HTTP error ' + response.status);
                }

                const renderer = NotebookUtils.getMarkdownRenderer();
                display.innerHTML = renderer.render(markdown);
                editor.hidden = true;
                display.hidden = false;
            } catch (error) {
                console.error('Ошибка сохранения текстовой ячейки:', error);
                alert('Ошибка при сохранении: ' + error.message);
            }
        });

        newCancelBtn.addEventListener('click', () => {
            if (mde) {
            
                const originalContent = textarea.value || '';
                mde.value(originalContent);
            }
            editor.hidden = true;
            display.hidden = false;
        });
    }

};
const runAll = function() {
    const cells = document.querySelectorAll('.cell')
    for (const cell of cells) {
        const id = cell.getAttribute('data-cell-id');
        if (!id) continue;

        // запускаем так же, как запускается одиночная ячейка
        notebookDetail.runCell(id);
    }
};
