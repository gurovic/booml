const notebookList = {
    config: null,

    init(config) {
        this.config = config;
        this.bindEvents();
    },

    bindEvents() {
        const container = document.getElementById('notebooks-container');
        if (container) {
            container.addEventListener('click', this.handleContainerClick.bind(this));
        }
    },

    handleContainerClick(e) {
        const target = e.target;
        const action = target.dataset.action;

        if (action === 'create-notebook') {
            this.createNotebook();
        }
    },

    async createNotebook() {
        try {
            const container = document.getElementById('notebooks-container');
            const createUrl = container.dataset.createNotebookUrl;
            const notebookUrlTemplate = container.dataset.notebookDetailUrl;

            const response = await fetch(createUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken
                }
            });

            if (!response.ok) throw new Error('HTTP error ' + response.status);

            const data = await response.json();

            if (data.status === 'success') {
                const detailUrl = notebookUrlTemplate.replace(/0\/?$/, `${data.notebook_id}/`);
                window.location.href = detailUrl;
            } else {
                alert('Ошибка: ' + (data.message || 'неизвестная ошибка'));
            }

        } catch (error) {
            console.error('Ошибка:', error);
            alert('Ошибка при создании блокнота: ' + error.message);
        }
    }
};
