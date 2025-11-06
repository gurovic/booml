const notebookDetail = {
    config: null,
    notebookElement: null,

    init(config) {
        this.config = config;
        this.notebookElement = document.querySelector(`[data-notebook-id="${config.notebookId}"]`);
        this.deleteUrlTemplate = this.notebookElement?.dataset.deleteUrlTemplate || '';
        this.saveOutputUrlTemplate = this.notebookElement?.dataset.saveOutputUrlTemplate || '';
        this.bindEvents();
        this.initializeCells();
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
            }

        } catch (error) {
            console.error('Ошибка:', error);
            alert('Ошибка при создании ячейки: ' + error.message);
        }
    },

    async runCell(cellId) {
        const code = document.querySelector(`[data-cell-id="${cellId}"] textarea`).value;
        const outputElement = document.getElementById(`output-${cellId}`);
        const runnerUrl = this.notebookElement.dataset.runnerUrl;
        const saveOutputUrl = this.buildCellUrl(this.saveOutputUrlTemplate, cellId);

        this.renderArtifacts(cellId, []);

        try {
            outputElement.innerHTML = '<div class="output-loading">Выполнение...</div>';
            outputElement.className = 'output running';

            const result = await NotebookUtils.runCode(code, runnerUrl, this.config.csrfToken);

            outputElement.innerHTML = result.output;
            outputElement.className = 'output success';

            this.renderArtifacts(cellId, result.artifacts);

            await NotebookUtils.saveCellOutput(
                this.config.notebookId,
                cellId,
                code,
                result.output,
                this.config.csrfToken,
                saveOutputUrl
            );

        } catch (error) {
            outputElement.innerHTML = `<div class="output-error"><strong>Ошибка:</strong> ${NotebookUtils.escapeHtml(error.message)}</div>`;
            outputElement.className = 'output error';

            const artifacts = Array.isArray(error?.artifacts) ? error.artifacts : [];
            this.renderArtifacts(cellId, artifacts);

            await NotebookUtils.saveCellOutput(
                this.config.notebookId,
                cellId,
                code,
                `<div class="output-error">Ошибка: ${NotebookUtils.escapeHtml(error.message)}</div>`,
                this.config.csrfToken,
                saveOutputUrl
            );
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
