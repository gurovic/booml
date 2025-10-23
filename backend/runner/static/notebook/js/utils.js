const NotebookUtils = {
    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;")
            .replace(/\n/g, '<br>')
            .replace(/ /g, '&nbsp;')
            .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
    },

    formatRunnerOutput(data) {
        let output = '';

        if (data.outputs && data.outputs.length > 0) {
            data.outputs.forEach(item => {
                if (item.type === 'text' && item.data.text) {
                    const escapedText = this.escapeHtml(item.data.text);
                    output += `<div class="output-text"><pre>${escapedText}</pre></div>`;
                }
            });
        }

        if (data.stderr) {
            const escapedStderr = this.escapeHtml(data.stderr);
            output += `<div class="output-stderr"><strong>STDERR:</strong><pre>${escapedStderr}</pre></div>`;
        }

        if (data.errors && data.errors.length > 0) {
            const errorMessages = data.errors.map(error =>
                `${error.code}: ${error.msg}`
            );
            const escapedErrors = this.escapeHtml(errorMessages.join('\n'));
            output += `<div class="output-errors"><strong>ERRORS:</strong><pre>${escapedErrors}</pre></div>`;
        }

        if (data.elapsed_ms !== undefined) {
            output += `<div class="output-stats">
                <hr>
                <small>Время выполнения: ${data.elapsed_ms}ms |
                Exit code: ${data.stats?.exit_code || 0}
                ${data.stats?.timeout ? '| ⚠️ Таймаут' : ''}
                </small>
            </div>`;
        }

        return output || '<div class="output-empty">No output</div>';
    },

    async runCode(code, runnerUrl, csrfToken) {
        try {
            const response = await fetch(runnerUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    code: code,
                    lang: 'python',
                    run_id: crypto.randomUUID()
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.ok) {
                return {
                    output: this.formatRunnerOutput(data),
                    run_id: data.run_id,
                    stats: {
                        execution_time_ms: data.elapsed_ms,
                        exit_code: data.stats?.exit_code || 0,
                        timeout: data.stats?.timeout || false
                    }
                };
            } else {
                const errorMsg = data.errors?.[0]?.msg || 'Execution failed';
                throw new Error(errorMsg);
            }

        } catch (error) {
            throw new Error(`Execution error: ${error.message}`);
        }
    },

    async saveCellOutput(notebookId, cellId, code, output, csrfToken, saveOutputUrl) {

        try {
            await fetch(saveOutputUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    code: code,
                    output: output
                })
            });
        } catch (error) {
            console.error('Ошибка сохранения:', error);
        }
    }
};