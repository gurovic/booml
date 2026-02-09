const notebookList = {
    config: null,

    init(config) {
        this.config = config;
        this.bindEvents();
        this.initImport();
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
        } else if (action === 'import-notebook') {
            this.triggerImportFileSelect();
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
    },

    initImport() {
        const fileInput = document.getElementById('import-file-input');
        if (fileInput) {
            // УБИРАЕМ accept атрибут - показываем все файлы
            // Сервер проверит содержимое файла
            fileInput.removeAttribute('accept');
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    this.importNotebook(file);
                }
                e.target.value = '';
            });
        }
    },

    triggerImportFileSelect() {
        // Создаем input динамически для лучшей совместимости с браузерами
        const input = document.createElement('input');
        input.type = 'file';
        // НЕ устанавливаем accept - показываем все файлы, сервер проверит содержимое
        // Это гарантирует, что .ipynb файлы будут доступны для выбора
        input.style.display = 'none';
        
        input.addEventListener('change', (event) => {
            const file = event.target.files?.[0];
            if (file) {
                this.importNotebook(file);
            }
            document.body.removeChild(input);
        });
        
        document.body.appendChild(input);
        input.click();
    },

    async importNotebook(file) {
        console.log('Импорт файла:', file.name, 'тип:', file.type, 'размер:', file.size);
        
        const fileInput = document.getElementById('import-file-input');
        const importUrl = fileInput?.dataset.importUrl;
        
        if (!importUrl) {
            this.showStatus('error', 'URL импорта недоступен');
            return;
        }

        // УБРАНА проверка расширения - сервер проверит содержимое файла
        // Это позволяет импортировать файлы даже если браузер не распознал расширение
        // Поддерживаются файлы .ipynb и .json в формате Jupyter Notebook

        try {
            this.showStatus('info', 'Импорт ноутбука...');
            
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(importUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken
                },
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || 'Ошибка импорта');
            }

            if (data.status === 'success') {
                let message = data.message || 'Ноутбук успешно импортирован';
                
                if (data.errors && data.errors.length > 0) {
                    message += `. Ошибок при создании ячеек: ${data.errors.length}`;
                }

                this.showStatus('success', message);
                
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                throw new Error(data.message || 'Неизвестная ошибка');
            }
        } catch (error) {
            console.error('Ошибка импорта:', error);
            this.showStatus('error', 'Ошибка при импорте ноутбука: ' + error.message);
        }
    },

    showStatus(type, message) {
        const statusElement = document.getElementById('import-status');
        if (!statusElement) {
            return;
        }

        statusElement.style.display = 'block';
        statusElement.textContent = message;
        
        statusElement.style.backgroundColor = type === 'success' ? '#d4edda' : 
                                             type === 'error' ? '#f8d7da' : 
                                             '#d1ecf1';
        statusElement.style.color = type === 'success' ? '#155724' : 
                                    type === 'error' ? '#721c24' : 
                                    '#0c5460';
        statusElement.style.border = `1px solid ${type === 'success' ? '#c3e6cb' : 
                                                  type === 'error' ? '#f5c6cb' : 
                                                  '#bee5eb'}`;
    }
};
