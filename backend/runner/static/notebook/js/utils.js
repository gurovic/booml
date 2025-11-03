const NotebookUtils = {
    _latexQueue: [],
    _markdownRenderer: null,

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
                    },
                    artifacts: Array.isArray(data.artifacts) ? data.artifacts : []
                };
            } else {
                const errorMsg = data.errors?.[0]?.msg || data.message || 'Execution failed';
                const error = new Error(errorMsg);
                error.artifacts = Array.isArray(data.artifacts) ? data.artifacts : [];
                throw error;
            }

        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            const wrappedError = new Error(`Execution error: ${message}`);

            if (error && typeof error === 'object' && 'artifacts' in error) {
                wrappedError.artifacts = error.artifacts;
            }

            throw wrappedError;
        }
    },

    async saveCellOutput(notebookId, cellId, code, output, csrfToken, saveOutputUrl) {

        if (!saveOutputUrl) {
            return { ok: false, error: new Error('URL сохранения недоступен') };
        }

        try {
            const response = await fetch(saveOutputUrl, {
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

            if (!response.ok) {
                return { ok: false, error: new Error(`HTTP error ${response.status}`) };
            }

            return { ok: true };

        } catch (error) {
            console.error('Ошибка сохранения:', error);
            return { ok: false, error };
        }
    },

    typesetLatex(target) {
        if (!target) {
            return;
        }

        if (window.MathJax?.typesetPromise) {
            window.MathJax.typesetPromise([target]).catch((error) => {
                console.error('MathJax typeset error:', error);
            });
        } else if (window.MathJax?.Hub) {
            window.MathJax.Hub.Queue(['Typeset', MathJax.Hub, target]);
        } else {
            if (!this._latexQueue.includes(target)) {
                this._latexQueue.push(target);
            }
        }
    },

    renderLatex(content, target) {
        if (!target) {
            return;
        }

        const sanitized = this.sanitizeLatexDocument(content);
        const markdown = this.latexToMarkdown(sanitized);
        const renderer = this.getMarkdownRenderer();
        const html = renderer.render(markdown);
        target.innerHTML = html;
        this.typesetLatex(target);
    },

    sanitizeLatexDocument(content) {
        if (!content) {
            return '';
        }

        return String(content)
            .replace(/\r\n?/g, '\n')
            .replace(/%.*$/gm, '')
            .replace(/\\documentclass(?:\[[^\]]*\])?\{[^}]*\}/g, '')
            .replace(/\\usepackage(?:\[[^\]]*\])?\{[^}]*\}/g, '')
            .replace(/\\begin\{document\}/g, '')
            .replace(/\\end\{document\}/g, '')
            .trim();
    },

    latexToMarkdown(content) {
        if (!content) {
            return '';
        }

        let text = content;
        let title = null;
        let author = null;
        let date = null;

        text = text.replace(/\\geometry\s*\{[\s\S]*?\}/g, '');
        text = text.replace(/\\lstset\s*\{[\s\S]*?\}/g, '');

        text = text.replace(/\\title\{([^}]*)\}/g, (_match, inner) => {
            title = this.convertInlineLatexToMarkdown(inner);
            return '';
        });

        text = text.replace(/\\author\{([^}]*)\}/g, (_match, inner) => {
            const normalized = inner.replace(/\\and/g, ', ');
            author = this.convertInlineLatexToMarkdown(normalized);
            return '';
        });

        text = text.replace(/\\date\{([^}]*)\}/g, (_match, inner) => {
            date = this.convertInlineLatexToMarkdown(inner);
            return '';
        });

        text = text.replace(/\\maketitle/g, '');

        const headingReplace = (pattern, hashes) => {
            text = text.replace(pattern, (_match, inner) => {
                const heading = this.convertInlineLatexToMarkdown(inner);
                return `\n${hashes} ${heading}\n`;
            });
        };

        headingReplace(/\\section\*?\{([^}]*)\}/g, '##');
        headingReplace(/\\subsection\*?\{([^}]*)\}/g, '###');
        headingReplace(/\\subsubsection\*?\{([^}]*)\}/g, '####');
        headingReplace(/\\paragraph\*?\{([^}]*)\}/g, '#####');

        text = text.replace(/\\begin\{itemize\}/g, '\n');
        text = text.replace(/\\end\{itemize\}/g, '\n');
        text = text.replace(/\\begin\{enumerate\}/g, '\n');
        text = text.replace(/\\end\{enumerate\}/g, '\n');
        text = text.replace(/\\item\s*/g, '\n- ');

        text = text.replace(/\\begin\{center\}/g, '\n<div class="latex-center" style="text-align:center;">');
        text = text.replace(/\\end\{center\}/g, '</div>\n');

        text = text.replace(/\\begin\{lstlisting\}(?:\[.*?\])?/gs, '\n```');
        text = text.replace(/\\end\{lstlisting\}/g, '\n```\n');

        text = text.replace(/\\hrule/g, '\n---\n');

        text = this.convertInlineLatexToMarkdown(text);

        text = text.replace(/\n{3,}/g, '\n\n');

        const blocks = [];
        if (title) {
            blocks.push(`# ${title}`);
        }
        if (author) {
            blocks.push(`**${author}**`);
        }
        if (date) {
            blocks.push(`_${date}_`);
        }
        blocks.push(text.trim());

        return blocks.filter(Boolean).join('\n\n').trim();
    },

    convertInlineLatexToMarkdown(text) {
        if (!text) {
            return '';
        }

        let output = String(text);

        const macroReplacements = [
            { pattern: /\\textbf\{([^{}]*)\}/g, wrap: (inner) => `**${this.convertInlineLatexToMarkdown(inner)}**` },
            { pattern: /\\textit\{([^{}]*)\}/g, wrap: (inner) => `*${this.convertInlineLatexToMarkdown(inner)}*` },
            { pattern: /\\emph\{([^{}]*)\}/g, wrap: (inner) => `*${this.convertInlineLatexToMarkdown(inner)}*` },
            { pattern: /\\underline\{([^{}]*)\}/g, wrap: (inner) => `<u>${this.convertInlineLatexToMarkdown(inner)}</u>` },
            { pattern: /\\texttt\{([^{}]*)\}/g, wrap: (inner) => `__CODE_OPEN__${this.convertInlineLatexToMarkdown(inner)}__CODE_CLOSE__` },
        ];

        macroReplacements.forEach(({ pattern, wrap }) => {
            output = output.replace(pattern, (_match, inner) => wrap(inner));
        });

        output = output.replace(/\\textcolor\{[^}]*\}\{([^}]*)\}/g, (_match, inner) => this.convertInlineLatexToMarkdown(inner));

        output = output.replace(/\\href\{([^}]*)\}\{([^}]*)\}/g, (_match, url, label) => {
            const labelMarkdown = this.convertInlineLatexToMarkdown(label);
            const safeUrl = this.escapeAttribute(url);
            return `[${labelMarkdown}](${safeUrl})`;
        });

        output = output.replace(/\\url\{([^}]*)\}/g, (_match, url) => {
            const safeUrl = this.escapeAttribute(url);
            return `<${safeUrl}>`;
        });

        output = output.replace(/\\%/g, '%')
            .replace(/\\#/g, '#')
            .replace(/\\\$/g, '$')
            .replace(/\\_/g, '_')
            .replace(/\\&/g, '&')
            .replace(/\\\^/g, '^');

        output = output.replace(/\\\\/g, '  \n');

        output = output.replace(/__CODE_OPEN__(.*?)__CODE_CLOSE__/g, (_match, inner) => {
            const escaped = inner.replace(/`/g, '\\`');
            return `\`${escaped}\``;
        });

        return output;
    },

    getMarkdownRenderer() {
        if (this._markdownRenderer) {
            return this._markdownRenderer;
        }

        const defaults = {
            html: true,
            linkify: true,
            breaks: true,
        };

        const renderer = typeof window.markdownit === 'function'
            ? window.markdownit(defaults)
            : {
                render: (value) => this.escapeHtml(String(value)).replace(/\n/g, '<br>')
            };

        this._markdownRenderer = renderer;
        return renderer;
    },

    escapeAttribute(value) {
        const sanitized = value == null ? '' : String(value).trim();
        if (!sanitized) {
            return '#';
        }
        try {
            return encodeURI(sanitized);
        } catch (_error) {
            return '#';
        }
    },

    flushLatexQueue() {
        if (!this._latexQueue || this._latexQueue.length === 0) {
            return;
        }

        const pendingTargets = this._latexQueue.slice();
        this._latexQueue.length = 0;

        if (window.MathJax?.typesetPromise) {
            window.MathJax.typesetPromise(pendingTargets).catch((error) => {
                console.error('MathJax typeset error:', error);
            });
        } else if (window.MathJax?.Hub) {
            pendingTargets.forEach((target) => {
                window.MathJax.Hub.Queue(['Typeset', MathJax.Hub, target]);
            });
        } else {
            this._latexQueue.push(...pendingTargets);
        }
    }
};

if (typeof window !== 'undefined') {
    window.NotebookUtils = NotebookUtils;
}
