const notebookDetail = {
    config: null,
    notebookElement: null,

    init(config) {
        this.config = config;
        this.notebookElement = document.querySelector(`[data-notebook-id="${config.notebookId}"]`);
        this.deleteUrlTemplate = this.notebookElement?.dataset.deleteUrlTemplate || '';
        this.saveOutputUrlTemplate = this.notebookElement?.dataset.saveOutputUrlTemplate || '';
        this.bindEvents();
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
    },

    handleNotebookClick(e) {
        const target = e.target;
        const action = target.dataset.action;
        const cellElement = target.closest('[data-cell-id]');
        const cellId = cellElement ? cellElement.dataset.cellId : null;

        if (action === 'create-cell') {
            this.createCell();
        }
        else if (action === 'run-cell' && cellId) {
            this.runCell(cellId);
        }
        else if (action === 'delete-cell' && cellId) {
            this.deleteCell(cellId, cellElement);
        }
    },

    async createCell() {
        try {
            const createCellUrl = this.notebookElement.dataset.createCellUrl;

            if (!createCellUrl) {
                throw new Error('URL создания ячейки недоступен');
            }

            const response = await fetch(createCellUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken
                }
            });

            if (!response.ok) throw new Error('HTTP error ' + response.status);

            const html = await response.text();
            const container = document.getElementById('cells-container');

            if (!container) {
                throw new Error('Контейнер для ячеек не найден');
            }

            container.insertAdjacentHTML('beforeend', html);

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

        try {
            outputElement.innerHTML = '<div class="output-loading">Выполнение...</div>';
            outputElement.className = 'output running';

            const result = await NotebookUtils.runCode(code, runnerUrl, this.config.csrfToken);

            outputElement.innerHTML = result.output;
            outputElement.className = 'output success';

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
    }
};
