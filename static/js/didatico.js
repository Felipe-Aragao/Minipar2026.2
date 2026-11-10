/**
 * MINIPAR 2026.2 — AMBIENTE DIDÁTICO DE COMPILAÇÃO
 * Lógica frontend com visualização D3 da AST, tabela interativa de tokens,
 * análise semântica em tempo real, geração de TAC, C++ e compilação nativa.
 */

document.addEventListener('DOMContentLoaded', () => {
    // ==========================================
    // 1. ESTADO DA APLICAÇÃO
    // ==========================================
    const state = {
        editor: null,
        currentFile: 'programa_didatico.minipar',
        lastAnalysis: null,
        activePhase: 'tokens',
        astZoom: null,
        astSvg: null,
        astRootNode: null,
        astMode: 'graph', // 'graph' ou 'json'
        tokenMarks: [],
        errorMarks: []
    };

    // Código inicial didático demonstrando concorrência e controle
    const INITIAL_CODE = `seq {
    # Programa Didático MiniPar 2026.2
    var x = 10;
    var y = 20;
    var soma = x + y;

    print("Soma inicial:", soma);

    # Bloco concorrente
    par {
        print("Executando Thread A: x =", x);
        print("Executando Thread B: y =", y);
    }

    print("Processo finalizado com sucesso!");
}`;

    // ==========================================
    // 2. INICIALIZAÇÃO DO CODEMIRROR
    // ==========================================
    const editorTextarea = document.getElementById('editor-source');
    state.editor = CodeMirror.fromTextArea(editorTextarea, {
        lineNumbers: true,
        mode: 'text/x-c++src',
        theme: 'default',
        matchBrackets: true,
        autoCloseBrackets: true,
        styleActiveLine: true,
        tabSize: 4,
        indentUnit: 4,
        lineWrapping: false
    });

    state.editor.setValue(INITIAL_CODE);

    state.editor.on('change', () => {
        updateEditorStats();
        invalidateAnalysis();
    });

    function invalidateAnalysis() {
        state.lastAnalysis = null;
        state.astRootNode = null;
        clearEditorErrorMarks();
        clearTokenHighlight();
        renderTokensView([]);
        renderSemanticView(null, [], []);
        renderTacView('');
        renderCppView('');
        clearAstCanvas();
        document.getElementById('ast-json-output').textContent = 'Analise o codigo atualizado para gerar a AST.';
        document.getElementById('editor-feedback').textContent = 'Codigo alterado. Execute a analise novamente.';
        setPipelineStatus('idle', 'Codigo alterado: analisar novamente');
    }

    function updateEditorStats() {
        const text = state.editor.getValue();
        const lines = state.editor.lineCount();
        const chars = text.length;
        document.getElementById('stat-lines').textContent = `Linhas: ${lines}`;
        document.getElementById('stat-chars').textContent = `Caracteres: ${chars}`;
    }
    updateEditorStats();

    // ==========================================
    // 3. ALTERNÂNCIA DE FASES (OS 7 BOTÕES)
    // ==========================================
    const phaseButtons = document.querySelectorAll('.phase-btn');
    const didacticViews = document.querySelectorAll('.didactic-view');

    function switchPhase(phaseKey) {
        state.activePhase = phaseKey;

        phaseButtons.forEach(btn => {
            if (btn.dataset.phase === phaseKey) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        didacticViews.forEach(view => {
            if (view.id === `view-${phaseKey}`) {
                view.classList.add('active');
            } else {
                view.classList.remove('active');
            }
        });

        // Se for a visão da AST e ainda não desenhou ou mudou tamanho, redesenha
        if (phaseKey === 'ast' && state.lastAnalysis && state.lastAnalysis.ast) {
            setTimeout(renderAstTree, 50);
        }
    }

    phaseButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            switchPhase(btn.dataset.phase);
        });
    });

    // ==========================================
    // 4. ANÁLISE COMPLETA VIA BACKEND (/api/analisar)
    // ==========================================
    async function runAnalysis() {
        const code = state.editor.getValue();
        setPipelineStatus('busy', 'Analisando fases...');
        clearEditorErrorMarks();

        try {
            const chkOpt = document.getElementById('chk-optimize');
            const otimizar = chkOpt ? chkOpt.checked : false;
            const resp = await fetch('/api/analisar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code, otimizar: otimizar })
            });

            if (!resp.ok) {
                throw new Error(`Erro na resposta do servidor (${resp.status})`);
            }

            const data = await resp.json();
            if (code !== state.editor.getValue()) return;
            state.lastAnalysis = data;
            state.astRootNode = null;

            // Renderizar cada fase
            renderTokensView(data.tokens || []);
            renderSemanticView(data.semantica, data.simbolos || [], data.erros || []);
            renderTacView(data.tac || '', data.otimizacao);
            renderCppView(data.cpp || '');

            if (data.ast) {
                document.getElementById('ast-json-output').textContent = JSON.stringify(data.ast, null, 2);
                renderAstTree();
            } else {
                clearAstCanvas();
                document.getElementById('ast-json-output').textContent = 'Nenhuma árvore sintática disponível (verifique erros de sintaxe).';
            }

            // Checagem de Erros
            if (data.erros && data.erros.length > 0) {
                handleErrors(data.erros);
                setPipelineStatus('error', `${data.erros.length} erro(s) detectado(s)`);
            } else {
                clearEditorFeedback();
                setPipelineStatus('ready', 'Pronto para compilar');
            }

        } catch (err) {
            console.error('Falha na análise:', err);
            setPipelineStatus('error', 'Falha ao conectar com compilador');
            showToast('Erro ao processar análise do compilador: ' + err.message);
        }
    }

    function setPipelineStatus(statusType, label) {
        const el = document.getElementById('pipeline-status');
        el.className = `pipeline-status ${statusType}`;
        el.querySelector('.status-label').textContent = label;
    }

    function handleErrors(errors) {
        const feedbackEl = document.getElementById('editor-feedback');
        const firstErr = errors[0];

        feedbackEl.className = 'editor-feedback error';
        feedbackEl.textContent = `[Fase ${firstErr.fase}] ${formatDiagnostic(firstErr)}`;

        // Destaca a linha do primeiro erro no CodeMirror
        if (firstErr.linha) {
            const lineIdx = firstErr.linha - 1;
            const mark = state.editor.addLineClass(lineIdx, 'background', 'cm-error-line');
            state.errorMarks.push({ line: lineIdx, mark: mark });
        }
    }

    function formatDiagnostic(error) {
        const position = error.linha ? `Linha ${error.linha}` : 'Posicao indisponivel';
        return `${position}${error.coluna ? `, coluna ${error.coluna}` : ''}: ${error.mensagem}`;
    }

    function clearEditorErrorMarks() {
        state.errorMarks.forEach(item => {
            state.editor.removeLineClass(item.line, 'background', 'cm-error-line');
        });
        state.errorMarks = [];
    }

    function clearEditorFeedback() {
        const feedbackEl = document.getElementById('editor-feedback');
        feedbackEl.className = 'editor-feedback';
        feedbackEl.textContent = '✓ Código sem erros aparentes';
    }

    // ==========================================
    // 5. RENDERIZAÇÃO DA VISÃO DE TOKENS (LÉXICO)
    // ==========================================
    let allTokens = [];

    function renderTokensView(tokens) {
        allTokens = tokens;
        document.getElementById('chip-total-tokens').textContent = `Total: ${tokens.length} tokens`;

        const unique = new Set(tokens.map(t => t.lexema)).size;
        document.getElementById('chip-unique-lexemes').textContent = `${unique} lexemas únicos`;

        applyTokensFilter();
    }

    function applyTokensFilter() {
        const searchVal = document.getElementById('token-search').value.toLowerCase().trim();
        const filterType = document.getElementById('token-filter-type').value;

        const filtered = allTokens.filter(t => {
            const matchSearch = !searchVal || t.lexema.toLowerCase().includes(searchVal);
            let matchType = true;
            if (filterType !== 'ALL') {
                if (filterType === 'IDENTIFIER') matchType = t.tipo === 'IDENTIFIER';
                else if (filterType === 'KEYWORD') matchType = ['CLASS', 'EXTENDS', 'NEW', 'FUNC', 'VAR', 'IF', 'ELSE', 'WHILE', 'DO', 'FOR', 'IN', 'BREAK', 'CONTINUE', 'RETURN', 'SEQ', 'PAR', 'FORK', 'JOIN', 'CORE', 'HOST', 'THIS', 'C_CHANNEL', 'SEND', 'RECEIVE', 'INPUT', 'PRINT', 'MATRIX', 'TYPE', 'BOOL_LITERAL'].includes(t.tipo);
                else if (filterType === 'NUMBER') matchType = t.tipo === 'NUMBER';
                else if (filterType === 'STRING') matchType = t.tipo === 'STRING_LITERAL';
                else if (filterType === 'OPERATOR') matchType = ['PLUS', 'MINUS', 'STAR', 'SLASH', 'MOD', 'ASSIGN', 'EQ', 'NEQ', 'NOT', 'LT', 'GT', 'LTE', 'GTE', 'AND', 'OR'].includes(t.tipo);
                else if (filterType === 'DELIMITER') matchType = ['LBRACE', 'RBRACE', 'LPAREN', 'RPAREN', 'LBRACKET', 'RBRACKET', 'COMMA', 'SEMICOLON', 'DOT'].includes(t.tipo);
            }
            return matchSearch && matchType;
        });

        const tbody = document.getElementById('tokens-tbody');
        tbody.innerHTML = '';

        if (filtered.length === 0) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Nenhum token correspondente aos filtros.</td></tr>';
            return;
        }

        filtered.forEach((tok, idx) => {
            const tr = document.createElement('tr');

            // Categoria do badge
            let badgeClass = 'badge-DELIMITER';
            if (tok.tipo === 'IDENTIFIER') badgeClass = 'badge-IDENTIFIER';
            else if (['CLASS', 'EXTENDS', 'NEW', 'FUNC', 'VAR', 'IF', 'ELSE', 'WHILE', 'DO', 'FOR', 'IN', 'BREAK', 'CONTINUE', 'RETURN', 'SEQ', 'PAR', 'FORK', 'JOIN', 'CORE', 'HOST', 'THIS', 'C_CHANNEL', 'SEND', 'RECEIVE', 'INPUT', 'PRINT', 'MATRIX', 'TYPE', 'BOOL_LITERAL'].includes(tok.tipo)) badgeClass = 'badge-KEYWORD';
            else if (tok.tipo === 'NUMBER') badgeClass = 'badge-NUMBER';
            else if (tok.tipo === 'STRING_LITERAL') badgeClass = 'badge-STRING';
            else if (['PLUS', 'MINUS', 'STAR', 'SLASH', 'MOD', 'ASSIGN', 'EQ', 'NEQ', 'NOT', 'LT', 'GT', 'LTE', 'GTE', 'AND', 'OR'].includes(tok.tipo)) badgeClass = 'badge-OPERATOR';

            tr.innerHTML = `
                <td>${idx + 1}</td>
                <td><span class="token-badge ${badgeClass}">${tok.tipo}</span></td>
                <td class="token-lexeme">${escapeHtml(tok.lexema)}</td>
                <td>${tok.linha}</td>
                <td>${tok.coluna !== null ? tok.coluna : '-'}</td>
            `;

            // Interatividade bidirecional: hover destaca no CodeMirror
            tr.addEventListener('mouseenter', () => highlightTokenInEditor(tok));
            tr.addEventListener('mouseleave', clearTokenHighlight);
            tr.addEventListener('click', () => {
                highlightTokenInEditor(tok, true);
            });

            tbody.appendChild(tr);
        });
    }

    document.getElementById('token-search').addEventListener('input', applyTokensFilter);
    document.getElementById('token-filter-type').addEventListener('change', applyTokensFilter);

    function highlightTokenInEditor(token, jump = false) {
        clearTokenHighlight();
        if (!token.linha) return;

        const line = token.linha - 1;
        const col = (token.coluna !== null && token.coluna > 0) ? (token.coluna - 1) : 0;
        const len = token.lexema ? token.lexema.length : 1;

        const from = { line: line, ch: col };
        const to = { line: line, ch: col + len };

        const mark = state.editor.markText(from, to, { className: 'cm-token-highlight' });
        state.tokenMarks.push(mark);

        if (jump) {
            state.editor.scrollIntoView({ from, to }, 100);
            state.editor.setCursor(from);
        }
    }

    function clearTokenHighlight() {
        state.tokenMarks.forEach(m => m.clear());
        state.tokenMarks = [];
    }

    // ==========================================
    // 6. VISUALIZAÇÃO INTERATIVA DA AST (D3.js)
    // ==========================================
    function astDictToD3(node) {
        if (!node || typeof node !== 'object' || !node.node_type) return null;

        const type = node.node_type;
        let label = type;
        const details = {};

        // Atributos descritivos
        for (const [k, v] of Object.entries(node)) {
            if (['node_type', 'line', 'col', 'coluna'].includes(k)) continue;
            if (typeof v !== 'object') {
                details[k] = v;
            }
        }

        if (details.name) label += `: ${details.name}`;
        else if (details.op) label += ` [${details.op}]`;
        else if (details.value !== undefined) label += `: ${details.value}`;

        // Subnós (filhos)
        const children = [];
        for (const [k, v] of Object.entries(node)) {
            if (v && typeof v === 'object' && v.node_type) {
                const c = astDictToD3(v);
                if (c) children.push(c);
            } else if (Array.isArray(v)) {
                v.forEach(item => {
                    if (item && typeof item === 'object' && item.node_type) {
                        const c = astDictToD3(item);
                        if (c) children.push(c);
                    }
                });
            }
        }

        const res = {
            label: label,
            type: type,
            line: node.line || null,
            col: node.col || null,
            details: details
        };

        if (children.length > 0) {
            res.children = children;
        }

        return res;
    }

    function clearAstCanvas() {
        const svg = d3.select('#ast-svg');
        svg.selectAll('*').remove();
        state.astRootNode = null;
        state.astSvg = null;
        state.astZoom = null;
    }

    function renderAstTree() {
        if (!state.lastAnalysis || !state.lastAnalysis.ast) return;
        const rawAst = state.lastAnalysis.ast;
        const d3Data = astDictToD3(rawAst);
        if (!d3Data) return;

        const container = document.getElementById('ast-canvas-wrapper');
        const width = container.clientWidth || 600;
        const height = container.clientHeight || 500;

        const svg = d3.select('#ast-svg');
        svg.selectAll('*').remove();

        const g = svg.append('g').attr('class', 'main-tree-group');

        // Configuração de Zoom e Pan
        const zoom = d3.zoom()
            .scaleExtent([0.2, 3])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        svg.call(zoom);
        state.astZoom = zoom;
        state.astSvg = svg;

        // Criação da Hierarquia D3
        const root = state.astRootNode || d3.hierarchy(d3Data);
        if (!state.astRootNode && root.descendants().length > 20) {
            root.eachAfter(node => {
                if (node.depth >= 2 && node.children) {
                    node._children = node.children;
                    node.children = null;
                }
            });
        }
        state.astRootNode = root;

        // A disposição horizontal mantém os rótulos legíveis em árvores largas.
        const nodeWidth = 160;
        const nodeHeight = 65;
        const treeLayout = d3.tree().nodeSize([nodeHeight + 25, nodeWidth + 55]);

        function update(source) {
            treeLayout(root);

            const nodes = root.descendants();
            const links = root.links();

            // Transição suave
            const duration = 250;

            // 1. LINKS (Curvas cúbicas verticais)
            const linkSelection = g.selectAll('path.ast-link')
                .data(links, d => d.target.id || (d.target.id = ++nodeIdCounter));

            linkSelection.enter()
                .append('path')
                .attr('class', 'ast-link')
                .attr('d', d3.linkHorizontal()
                    .x(d => d.y)
                    .y(d => d.x)
                );

            linkSelection.transition().duration(duration)
                .attr('d', d3.linkHorizontal()
                    .x(d => d.y)
                    .y(d => d.x)
                );

            linkSelection.exit().remove();

            // 2. NÓS
            const nodeSelection = g.selectAll('g.ast-node')
                .data(nodes, d => d.id || (d.id = ++nodeIdCounter));

            const nodeEnter = nodeSelection.enter()
                .append('g')
                .attr('class', 'ast-node')
                .attr('transform', d => `translate(${d.y},${d.x})`)
                .on('click', (event, d) => {
                    // Colapsar / Expandir nó ao clicar
                    if (d.children) {
                        d._children = d.children;
                        d.children = null;
                    } else if (d._children) {
                        d.children = d._children;
                        d._children = null;
                    }
                    update(d);
                })
                .on('mouseenter', (event, d) => showAstTooltip(event, d))
                .on('mouseleave', hideAstTooltip);

            // Retângulo do Nó
            nodeEnter.append('rect')
                .attr('x', -nodeWidth / 2)
                .attr('y', -nodeHeight / 2)
                .attr('width', nodeWidth)
                .attr('height', nodeHeight)
                .attr('fill', d => getNodeColors(d.data.type).bg)
                .attr('stroke', d => getNodeColors(d.data.type).border);

            // Texto do Tipo de Nó
            nodeEnter.append('text')
                .attr('x', 0)
                .attr('y', -10)
                .attr('text-anchor', 'middle')
                .attr('fill', 'currentColor')
                .text(d => truncate(d.data.type, 18));

            // Subtexto / Detalhes (Nome ou Operador)
            nodeEnter.append('text')
                .attr('class', 'node-subtext')
                .attr('x', 0)
                .attr('y', 10)
                .attr('text-anchor', 'middle')
                .text(d => {
                    const dt = d.data.details || {};
                    if (dt.name) return truncate(`name: ${dt.name}`, 18);
                    if (dt.op) return truncate(`op: ${dt.op}`, 18);
                    if (dt.value !== undefined) {
                        const valStr = typeof dt.value === 'string' ? `"${dt.value}"` : String(dt.value);
                        return truncate(valStr, 18);
                    }
                    return d.data.line ? `linha ${d.data.line}` : '';
                });

            // Tooltip nativo SVG para exibir o valor completo ao passar o mouse
            nodeEnter.append('title')
                .text(d => {
                    const dt = d.data.details || {};
                    let tip = d.data.type;
                    if (d.data.line) tip += ` (Linha ${d.data.line})`;
                    if (dt.name) tip += `\nIdentificador: ${dt.name}`;
                    if (dt.op) tip += `\nOperador: ${dt.op}`;
                    if (dt.value !== undefined) tip += `\nValor completo: ${dt.value}`;
                    return tip;
                });

            // Indicador de colapsado (+)
            nodeEnter.append('text')
                .attr('class', 'ast-collapse-indicator')
                .attr('x', nodeWidth / 2 - 12)
                .attr('y', nodeHeight / 2 - 8)
                .text(d => d._children ? '+' : (d.children ? '−' : ''));

            // Transição dos nós existentes
            const nodeUpdate = nodeSelection.merge(nodeEnter);
            nodeUpdate.transition().duration(duration)
                .attr('transform', d => `translate(${d.y},${d.x})`);

            nodeUpdate.select('.ast-collapse-indicator')
                .text(d => d._children ? '+' : (d.children ? '−' : ''));

            nodeSelection.exit().remove();
        }

        let nodeIdCounter = 0;
        update(root);

        // Centralizar árvore no viewport inicial
        resetAstView(width, height);
    }

    function getNodeColors(type) {
        if (type === 'Program') return { bg: 'var(--node-bg-program)', border: 'var(--node-border-program)' };
        if (['SeqBlock', 'ParBlock', 'ForkStmt', 'JoinStmt'].includes(type)) return { bg: 'var(--node-bg-block)', border: 'var(--node-border-block)' };
        if (['VarDecl', 'ClassDecl', 'FuncDecl'].includes(type)) return { bg: 'var(--node-bg-decl)', border: 'var(--node-border-decl)' };
        if (['IfStmt', 'WhileStmt', 'ForStmt', 'DoWhileStmt'].includes(type)) return { bg: 'var(--node-bg-control)', border: 'var(--node-border-control)' };
        return { bg: 'var(--node-bg-expr)', border: 'var(--node-border-expr)' };
    }

    function resetAstView(w, h) {
        if (!state.astSvg || !state.astZoom) return;
        const svg = state.astSvg;
        const zoom = state.astZoom;
        const width = w || document.getElementById('ast-canvas-wrapper').clientWidth;

        const height = h || document.getElementById('ast-canvas-wrapper').clientHeight || 500;
        const nodes = state.astRootNode ? state.astRootNode.descendants() : [];
        if (!nodes.length) return;
        const minX = Math.min(...nodes.map(n => n.y)) - 90;
        const maxX = Math.max(...nodes.map(n => n.y)) + 90;
        const minY = Math.min(...nodes.map(n => n.x)) - 40;
        const maxY = Math.max(...nodes.map(n => n.x)) + 40;
        const scale = Math.min(1, (width - 40) / (maxX - minX), (height - 40) / (maxY - minY));
        svg.transition().duration(300).call(zoom.transform,
            d3.zoomIdentity.translate(width / 2 - (minX + maxX) * scale / 2,
                height / 2 - (minY + maxY) * scale / 2).scale(scale));
    }

    function showAstTooltip(event, d) {
        const tooltip = document.getElementById('ast-tooltip');
        let html = `<strong>${escapeHtml(d.data.type)}</strong><br>`;
        if (d.data.line) html += `Linha: ${d.data.line}${d.data.col ? `, coluna: ${d.data.col}` : ''}<br>`;
        for (const [k, v] of Object.entries(d.data.details || {})) {
            html += `<span style="color:var(--text-muted)">${escapeHtml(k)}:</span> ${escapeHtml(String(v))}<br>`;
        }
        tooltip.innerHTML = html;
        tooltip.style.display = 'block';

        const containerRect = document.getElementById('ast-canvas-wrapper').getBoundingClientRect();
        tooltip.style.left = (event.clientX - containerRect.left + 15) + 'px';
        tooltip.style.top = (event.clientY - containerRect.top + 15) + 'px';

        // Destaca linha correspondente no CodeMirror
        if (d.data.line) {
            clearTokenHighlight();
            const line = d.data.line - 1;
            const mark = state.editor.markText({ line, ch: 0 }, { line, ch: 100 }, { className: 'cm-token-highlight' });
            state.tokenMarks.push(mark);
        }
    }

    function hideAstTooltip() {
        const tooltip = document.getElementById('ast-tooltip');
        tooltip.style.display = 'none';
        clearTokenHighlight();
    }

    // Botões de controle da AST
    document.getElementById('btn-ast-zoom-in').addEventListener('click', () => {
        if (state.astSvg && state.astZoom) {
            state.astSvg.transition().duration(200).call(state.astZoom.scaleBy, 1.3);
        }
    });

    document.getElementById('btn-ast-zoom-out').addEventListener('click', () => {
        if (state.astSvg && state.astZoom) {
            state.astSvg.transition().duration(200).call(state.astZoom.scaleBy, 0.77);
        }
    });

    document.getElementById('btn-ast-fit').addEventListener('click', () => {
        resetAstView();
    });

    document.getElementById('btn-ast-expand-all').addEventListener('click', () => {
        if (state.astRootNode) {
            function expand(n) {
                if (n._children) {
                    n.children = n._children;
                    n._children = null;
                }
                if (n.children) n.children.forEach(expand);
            }
            expand(state.astRootNode);
            renderAstTree();
        }
    });

    document.getElementById('btn-ast-toggle-mode').addEventListener('click', () => {
        const canvas = document.getElementById('ast-canvas-wrapper');
        const jsonBox = document.getElementById('ast-json-wrapper');
        const btn = document.getElementById('btn-ast-toggle-mode');

        if (state.astMode === 'graph') {
            state.astMode = 'json';
            canvas.style.display = 'none';
            jsonBox.style.display = 'block';
            btn.textContent = 'Ver Gráfica';
        } else {
            state.astMode = 'graph';
            canvas.style.display = 'block';
            jsonBox.style.display = 'none';
            btn.textContent = 'Ver JSON';
            setTimeout(renderAstTree, 50);
        }
    });

    // ==========================================
    // 7. RENDERIZAÇÃO DA VISÃO SEMÂNTICA
    // ==========================================
    function renderSemanticView(semantica, simbolos, erros) {
        const card = document.getElementById('semantic-status-card');
        const title = document.getElementById('semantic-status-title');
        const desc = document.getElementById('semantic-status-desc');
        const icon = document.getElementById('semantic-status-icon');

        const semanticErrors = (erros || []).filter(e => e.fase === 'semantica');
        const hasSemanticError = semanticErrors.length > 0 || (semantica && semantica.sucesso === false);
        const notExecuted = !semantica || semantica.sucesso == null;
        card.classList.toggle('pending', notExecuted);

        if (notExecuted) {
            card.classList.remove('invalid');
            icon.textContent = '…';
            title.textContent = 'Analise semantica nao executada';
            desc.textContent = 'Execute a analise e corrija eventuais erros lexicos ou sintaticos.';
        } else if (hasSemanticError) {
            card.classList.add('invalid');
            icon.textContent = '⚠';
            title.textContent = 'Inconsistências Semânticas Encontradas';
            desc.textContent = semanticErrors.length > 0
                ? semanticErrors.map(formatDiagnostic).join(' | ')
                : 'Falha na checagem de tipos ou escopos.';
        } else {
            card.classList.remove('invalid');
            icon.textContent = '✓';
            title.textContent = 'Semântica Válida';
            desc.textContent = 'Declarações, tipos e isolamento de tarefas concorrentes validados com sucesso.';
        }

        // Tabela de Símbolos
        document.getElementById('badge-symbols-count').textContent = `${simbolos.length} símbolos`;
        const tbody = document.getElementById('symbols-tbody');
        tbody.innerHTML = '';

        if (simbolos.length === 0) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Nenhum símbolo registrado na tabela.</td></tr>';
        } else {
            simbolos.forEach(sym => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${escapeHtml(sym.nome)}</strong></td>
                    <td><code>${escapeHtml(sym.tipo || 'inferred')}</code></td>
                    <td>Escopo #${sym.escopo}</td>
                    <td>${escapeHtml(sym.classe || sym.funcao || 'Global')}</td>
                    <td>${sym.linha || '-'}</td>
                    <td>${sym.coluna || '-'}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    }

    // ==========================================
    // 8. RENDERIZAÇÃO DA VISÃO TAC E C++
    // ==========================================
    function renderTacView(tacText, otimizacao) {
        const el = document.getElementById('tac-output');
        el.textContent = tacText || 'Nenhum código TAC gerado (verifique se há erros nas fases anteriores).';

        const banner = document.getElementById('tac-optimization-banner');
        const statsEl = document.getElementById('tac-optimization-stats');
        if (banner && statsEl) {
            if (otimizacao && otimizacao.ativa) {
                banner.style.display = 'block';
                let detalhe = `Nós da AST: ${otimizacao.nos_antes} → ${otimizacao.nos_depois} (${otimizacao.reducao_pct}% de redução).`;
                if (otimizacao.transformacoes && otimizacao.transformacoes.length > 0) {
                    detalhe += `\nTransformações aplicadas (${otimizacao.transformacoes.length}):\n• ` + otimizacao.transformacoes.join('\n• ');
                } else {
                    detalhe += '\nNenhuma simplificação necessária para este código.';
                }
                statsEl.innerText = detalhe;
                statsEl.style.whiteSpace = 'pre-line';
            } else {
                banner.style.display = 'none';
            }
        }
    }

    function renderCppView(cppText) {
        const el = document.getElementById('cpp-output');
        el.textContent = cppText || 'Nenhum código C++ gerado (verifique se há erros nas fases anteriores).';
    }

    // ==========================================
    // 9. EXECUÇÃO DO PROGRAMA (/api/compile)
    // ==========================================
    const btnRun = document.getElementById('btn-run-code');
    btnRun.addEventListener('click', async () => {
        const code = state.editor.getValue();
        const inputsRaw = document.getElementById('terminal-user-input').value;
        const inputs = inputsRaw === '' ? [] : inputsRaw.replace(/\r\n?/g, '\n').split('\n');

        switchPhase('execution');
        const termScreen = document.getElementById('didactic-terminal-output');
        const termStatus = document.getElementById('term-status');
        const termTime = document.getElementById('term-time');

        termScreen.textContent = 'Compilando código C++ via g++ -O3 e executando...\n';
        termStatus.textContent = 'Status: Em execução...';
        termTime.textContent = 'Tempo: ...';

        const startTime = performance.now();

        try {
            const chkOpt = document.getElementById('chk-optimize');
            const otimizar = chkOpt ? chkOpt.checked : false;
            const resp = await fetch('/api/compile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code: code,
                    filename: state.currentFile,
                    inputs: inputs,
                    otimizar: otimizar
                })
            });

            const data = await resp.json();
            const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);
            termTime.textContent = `Tempo total: ${elapsed}s`;

            if (data.success) {
                termStatus.textContent = 'Status: Sucesso (Código 0)';
                termScreen.textContent = (data.execution_stdout ?? data.stdout) || '(Execução finalizada sem saída impressa)';
            } else {
                termStatus.textContent = 'Status: Falha na compilação ou execução';
                termScreen.textContent = (data.stderr || data.stdout || data.error || 'Erro desconhecido durante o processo.');
            }
        } catch (err) {
            termStatus.textContent = 'Status: Erro de conexão';
            termScreen.textContent = 'Falha ao comunicar com o servidor: ' + err.message;
        }
    });

    // ==========================================
    // 10. COMPILAR E BAIXAR EXECUTÁVEL (.EXE)
    // ==========================================
    const btnDownloadExe = document.getElementById('btn-download-exe');
    btnDownloadExe.addEventListener('click', async () => {
        const code = state.editor.getValue();
        setPipelineStatus('busy', 'Gerando executável nativo (.exe)...');
        showToast('Compilando com g++ -O3 para gerar executável...');

        try {
            const chkOpt = document.getElementById('chk-optimize');
            const otimizar = chkOpt ? chkOpt.checked : false;
            const resp = await fetch('/api/download_exe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code: code,
                    filename: state.currentFile,
                    otimizar: otimizar
                })
            });

            if (!resp.ok) {
                const errJson = await resp.json().catch(() => ({}));
                throw new Error(errJson.error || `Falha do servidor (${resp.status})`);
            }

            const blob = await resp.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;

            const disposition = resp.headers.get('Content-Disposition') || '';
            const match = disposition.match(/filename="?([^";]+)"?/i);
            const exeName = match ? match[1] : state.currentFile.replace(/\.minipar$/, '');
            a.download = exeName;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            a.remove();

            setPipelineStatus('ready', 'Executável gerado!');
            showToast(`Download de '${exeName}' concluído com sucesso!`);
        } catch (err) {
            console.error('Falha no download:', err);
            setPipelineStatus('error', 'Falha ao compilar .exe');
            showToast('Erro ao gerar executável: ' + err.message);
        }
    });

    // ==========================================
    // 11. CARREGAR EXEMPLOS DISPONÍVEIS (/api/tests)
    // ==========================================
    const selectExample = document.getElementById('select-example');

    async function loadAvailableTests() {
        try {
            const resp = await fetch('/api/tests');
            if (!resp.ok) return;
            const data = await resp.json();

            selectExample.innerHTML = '<option value="" disabled selected>Selecione um programa...</option>';
            (data.tests || []).forEach(file => {
                const opt = document.createElement('option');
                opt.value = file;
                // Deixa o nome mais amigável
                opt.textContent = file
                    .replace('.minipar', '')
                    .replace(/^teste/, 'Teste ')
                    .replace(/_/g, ' ');
                selectExample.appendChild(opt);
            });
        } catch (e) {
            console.warn('Não foi possível listar testes:', e);
        }
    }
    loadAvailableTests();

    selectExample.addEventListener('change', async (e) => {
        const filename = e.target.value;
        if (!filename) return;

        showToast(`Carregando '${filename}'...`);
        try {
            const resp = await fetch('/api/get_test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: filename })
            });

            if (resp.ok) {
                const data = await resp.json();
                state.currentFile = filename;
                document.getElementById('current-filename').textContent = filename;
                state.editor.setValue(data.code || '');
                runAnalysis();
                showToast(`'${filename}' carregado com sucesso.`);
            }
        } catch (err) {
            showToast('Erro ao carregar teste: ' + err.message);
        }
    });

    // ==========================================
    // 12. FERRAMENTAS DO EDITOR (COPIAR, LIMPAR)
    // ==========================================
    document.getElementById('btn-analyze').addEventListener('click', runAnalysis);
    const chkOptEl = document.getElementById('chk-optimize');
    if (chkOptEl) {
        chkOptEl.addEventListener('change', runAnalysis);
    }

    document.getElementById('btn-clear-code').addEventListener('click', () => {
        state.editor.setValue('');
        state.editor.focus();
    });

    document.getElementById('btn-copy-code').addEventListener('click', () => {
        copyToClipboard(state.editor.getValue(), 'Código MiniPar copiado!');
    });

    document.getElementById('btn-copy-tac').addEventListener('click', () => {
        const text = document.getElementById('tac-output').textContent;
        copyToClipboard(text, 'TAC copiado para a área de transferência!');
    });

    document.getElementById('btn-copy-cpp').addEventListener('click', () => {
        const text = document.getElementById('cpp-output').textContent;
        copyToClipboard(text, 'Código C++ copiado para a área de transferência!');
    });

    document.getElementById('btn-clear-terminal').addEventListener('click', () => {
        document.getElementById('didactic-terminal-output').textContent = 'Terminal limpo.';
    });

    // Alternar tema claro / escuro
    const btnTheme = document.getElementById('btn-theme-toggle');
    btnTheme.addEventListener('click', () => {
        document.body.classList.toggle('theme-dark');
        const isDark = document.body.classList.contains('theme-dark');
        localStorage.setItem('minipar_theme', isDark ? 'dark' : 'light');
        if (state.lastAnalysis && state.lastAnalysis.ast) {
            renderAstTree();
        }
        if (state.editor) {
            state.editor.refresh();
        }
    });

    if (localStorage.getItem('minipar_theme') === 'dark') {
        document.body.classList.add('theme-dark');
        setTimeout(() => {
            if (state.editor) state.editor.refresh();
        }, 100);
    }

    // ==========================================
    // 13. FUNÇÕES UTILITÁRIAS
    // ==========================================
    function copyToClipboard(text, successMsg) {
        navigator.clipboard.writeText(text).then(() => {
            showToast(successMsg);
        }).catch(e => {
            showToast('Falha ao copiar: ' + e);
        });
    }

    function showToast(msg) {
        const t = document.getElementById('toast');
        t.textContent = msg;
        t.classList.add('show');
        setTimeout(() => {
            t.classList.remove('show');
        }, 3200);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function truncate(str, max) {
        if (!str) return '';
        return str.length > max ? str.substring(0, max - 1) + '…' : str;
    }

    // ==========================================
    // 14. DIVISÓRIA REDIMENSIONÁVEL & RETRÁTIL (SPLIT-RESIZER)
    // ==========================================
    const workspaceContainer = document.querySelector('.workspace-container');
    const paneEditor = document.querySelector('.pane-editor');
    const paneResizer = document.getElementById('pane-resizer');
    const btnToggleEditor = document.getElementById('btn-toggle-editor');
    const resizerToggleIcon = document.getElementById('resizer-toggle-icon');

    let isDraggingResizer = false;

    // Restaurar proporção salva do editor
    const savedRatio = localStorage.getItem('minipar_editor_ratio');
    if (savedRatio && !isNaN(savedRatio)) {
        const ratio = parseFloat(savedRatio);
        if (ratio >= 15 && ratio <= 80) {
            paneEditor.style.width = ratio + '%';
        }
    }

    if (paneResizer) {
        paneResizer.addEventListener('mousedown', (e) => {
            if (e.target.closest('#btn-toggle-editor')) return;
            isDraggingResizer = true;
            paneResizer.classList.add('is-dragging');
            document.body.classList.add('is-resizing');
        });
    }

    document.addEventListener('mousemove', (e) => {
        if (!isDraggingResizer || !workspaceContainer || !paneEditor) return;

        if (workspaceContainer.classList.contains('editor-collapsed')) {
            toggleEditorCollapse(false);
        }

        const containerRect = workspaceContainer.getBoundingClientRect();
        const mouseX = e.clientX - containerRect.left;
        const totalWidth = containerRect.width;

        const minPx = 180;
        const maxPx = totalWidth - 220;

        let clampedPx = Math.max(minPx, Math.min(maxPx, mouseX));
        let pct = (clampedPx / totalWidth) * 100;

        paneEditor.style.width = pct.toFixed(2) + '%';
        localStorage.setItem('minipar_editor_ratio', pct.toFixed(2));

        if (state.editor) {
            state.editor.refresh();
        }

        if (state.activePhase === 'ast') {
            adjustAstViewOnResize();
        }
    });

    document.addEventListener('mouseup', () => {
        if (isDraggingResizer) {
            isDraggingResizer = false;
            if (paneResizer) paneResizer.classList.remove('is-dragging');
            document.body.classList.remove('is-resizing');

            if (state.editor) {
                state.editor.refresh();
            }
            if (state.activePhase === 'ast' && state.lastAnalysis && state.lastAnalysis.ast) {
                renderAstTree();
            }
        }
    });

    // Duplo clique na divisória centraliza / restaura layout padrão
    if (paneResizer) {
        paneResizer.addEventListener('dblclick', (e) => {
            if (e.target.closest('#btn-toggle-editor')) return;

            paneEditor.style.width = '45%';
            localStorage.removeItem('minipar_editor_ratio');
            if (workspaceContainer.classList.contains('editor-collapsed')) {
                toggleEditorCollapse(false);
            }
            if (state.editor) state.editor.refresh();
            if (state.activePhase === 'ast') renderAstTree();
            showToast('Divisória restaurada para o padrão (45% / 55%).');
        });
    }

    // Botão retrátil: recolher ou expandir editor com 1 clique
    if (btnToggleEditor) {
        btnToggleEditor.addEventListener('click', (e) => {
            e.stopPropagation();
            const isCollapsed = workspaceContainer.classList.contains('editor-collapsed');
            toggleEditorCollapse(!isCollapsed);
        });
    }

    function toggleEditorCollapse(collapse) {
        if (collapse) {
            workspaceContainer.classList.add('editor-collapsed');
            if (resizerToggleIcon) resizerToggleIcon.innerHTML = '<polyline points="9 18 15 12 9 6"></polyline>';
            if (btnToggleEditor) btnToggleEditor.title = 'Expandir editor de código';
            showToast('Editor de código recolhido.');
        } else {
            workspaceContainer.classList.remove('editor-collapsed');
            if (resizerToggleIcon) resizerToggleIcon.innerHTML = '<polyline points="15 18 9 12 15 6"></polyline>';
            if (btnToggleEditor) btnToggleEditor.title = 'Recolher editor de código';
            showToast('Editor de código expandido.');
        }

        setTimeout(() => {
            if (state.editor) state.editor.refresh();
            if (state.activePhase === 'ast' && state.lastAnalysis && state.lastAnalysis.ast) {
                renderAstTree();
            }
        }, 50);
    }

    let resizeDebounce = null;
    function adjustAstViewOnResize() {
        clearTimeout(resizeDebounce);
        resizeDebounce = setTimeout(() => {
            if (state.activePhase === 'ast') {
                resetAstView();
            }
        }, 120);
    }

    window.addEventListener('resize', () => {
        if (state.editor) state.editor.refresh();
        if (state.activePhase === 'ast') adjustAstViewOnResize();
    });


    // Disparar análise inicial
    setTimeout(runAnalysis, 150);
});
