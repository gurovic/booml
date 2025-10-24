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
        } else if (data.output) {
            const escapedText = this.escapeHtml(data.output);
            output += `<div class="output-text"><pre>${escapedText}</pre></div>`;
        }

        if (data.stderr) {
            const escapedStderr = this.escapeHtml(data.stderr);
            output += `<div class="output-stderr"><strong>STDERR:</strong><pre>${escapedStderr}</pre></div>`;
        }

        if (data.errors && data.errors.length > 0) {
            const errorMessages = data.errors.map(error =>
                error.code && error.msg ? `${error.code}: ${error.msg}` : error.msg || error
            );
            const escapedErrors = this.escapeHtml(errorMessages.join('\n'));
            output += `<div class="output-errors"><strong>ERRORS:</strong><pre>${escapedErrors}</pre></div>`;
        }

        const elapsed = data.elapsed_ms ?? data.stats?.execution_time_ms;
        if (elapsed !== undefined) {
            output += `<div class="output-stats">
                <hr>
                <small>Время выполнения: ${elapsed}ms |
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

            if (data.status === 'success') {
                return {
                    output: this.formatRunnerOutput(data),
                    run_id: data.run_id,
                    stats: {
                        execution_time_ms: data.stats?.execution_time_ms ?? data.elapsed_ms ?? null,
                        exit_code: data.stats?.exit_code || 0,
                        timeout: data.stats?.timeout || false
                    }
                };
            } else {
                const errorMsg = data.errors?.[0]?.msg || data.message || 'Execution failed';
                throw new Error(errorMsg);
            }

        } catch (error) {
            throw new Error(`Execution error: ${error.message}`);
        }
    },

    async saveCellOutput(notebookId, cellId, code, output, csrfToken, saveOutputUrl) {

        if (!saveOutputUrl) {
            return;
        }

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