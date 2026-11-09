# Compilador MiniPar
Trabalho de Compiladores - UFAL 


Arquitetura orientada a objetos baseada na versão C++ original, agora expandida para incluir **Geração de Código Intermediário (TAC)** de 3 endereços e uma nova **IDE Web**, capaz de gerar, compilar e executar o código C++ produzido pelo compilador.
Grupo MiniPar 2026.2:

- Érico Almeida Bernardino
- Felipe Lima Aragão
- Lucas Trindade de Souza

A versão 2026.2 reutiliza o projeto [MiniPar 2026.1](https://github.com/luizwhirl/minipar-improvement).
Autores da base 2026.1:

Emanuele Vitória de Jesus Lima - [Manu-Vii](https://github.com/Manu-Vii)

José Lucas de Oliveira Quintela - [lucasqtl](https://github.com/lucasqtl)

Luiz Miguel de Melo Bomfim - [luizwhirl](https://github.com/luizwhirl)

---

## Estrutura do Projeto

```text
minipar_python/
├── src/
│   ├── ast_nodes.py      # Nós da AST (dataclasses)
│   ├── lexer.py          # Analisador Léxico
│   ├── parser.py         # Analisador Sintático
│   ├── semantic.py       # Analisador Semântico
│   ├── tac.py            # Gerador de Código Intermediário (TAC)
│   ├── codegen.py        # Gerador de Código C++
│   └── cpp_template.py   # Template base em C++
├── static/               # Arquivos estáticos da IDE Web (CSS, JS)
├── templates/            # Arquivos HTML da IDE Web
├── tests/                # Exemplos e testes .minipar
├── output/               # Arquivos gerados (.cpp, .tac e executáveis)
├── temp_code/            # Códigos temporários executados pela IDE
├── app.py                # Servidor Flask da Interface Web
├── main.py               # Ponto de entrada principal (CLI e Interativo)
├── menu.py               # Menu interativo para terminal
├── requirements.txt      # Dependências Python
└── README.md
```

---

## Requisitos

- Python 3.10 ou superior (validação realizada com Python 3.12)
- `g++` disponível no PATH (para compilar o código C++ gerado)
- Flask (para executar a IDE Web)

Instalação das dependências:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

---

## Como Usar

O compilador oferece múltiplas formas de interação.

### 1. Menu Interativo (Terminal ou IDE Web)

Execute o programa sem argumentos:

```bash
python main.py
```

Opções disponíveis:

- **[1] Modo Terminal**: navegação pelos testes através de um menu textual.
- **[2] Modo Web Interface**: inicia o servidor Flask.

Após iniciar a interface web, acesse:

```text
http://127.0.0.1:5000
```

As duas interfaces ficam disponíveis no mesmo servidor:

- `http://127.0.0.1:5000/` ou `/didatico`: ambiente didático com Tokens, AST, Semântica, TAC e C++.
- `http://127.0.0.1:5000/ide`: IDE do desenvolvedor preservada.

A entrada do ambiente didático usa **uma resposta por linha**. Espaços e vírgulas
são preservados, inclusive em expressões do Teste 11. A análise gera C++ em memória;
compilação, execução e download são ações separadas. As bibliotecas D3 e CodeMirror
estão incluídas localmente e não exigem acesso a CDNs.

[Guia da interface didática](docs/interface_didatica.md) ·
[Pseudocódigos dos itens 3 a 6](docs/pseudocodigos_frontend.md)

A IDE permite:

- Editar código MiniPar
- Compilar o programa
- Visualizar o código TAC gerado
- Visualizar o código C++ gerado
- Executar o programa e ver a saída

### 2. Execução Direta (CLI)

Para compilar um arquivo específico:

```bash
python main.py tests/teste3_neuronio.minipar
```

O nome do arquivo de saída é opcional. Por padrão, será utilizado o mesmo nome do arquivo `.minipar`.

Os arquivos gerados (`.cpp`, `.tac` e executáveis) serão armazenados na pasta `output/`.

---

## Fases do Compilador

| Fase | Arquivos | Descrição |
|------|----------|------------|
| 1 | `lexer.py` / `parser.py` | Tokenização do código-fonte e construção da AST |
| 2 | `semantic.py` | Verificação de declarações, redeclarações e escopo |
| 3 | `tac.py` | Geração de Código Intermediário (TAC) |
| 4 | `codegen.py` | Geração de código C++ e compilação automática via `g++ -O3` |

## Testes do front-end

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests
```

A suíte verifica tokens, AST, símbolos, diagnósticos e TAC, incluindo destinos de
`fork`, escopo e `join`. Os testes dos componentes dispensam g++ e conexões de rede.
`test_integracao_backend.py` compila e executa casos de regressão quando g++ está
disponível, cobrindo tarefas aninhadas, barreira, capturas, retornos e impressão de listas.
Para compilar e executar os programas de exemplo, use `python tests/run_all.py`.

---

## Sintaxe MiniPar

Exemplo:

```minipar
seq {
    var x = 42;

    print("Valor:", x);

    par {
        print("Thread A");
        print("Thread B");
    }
}
```

### Comandos Disponíveis

| Sintaxe | Descrição |
|----------|------------|
| `seq { ... }` | Bloco sequencial |
| `par { ... }` | Bloco paralelo (cada instrução gera uma thread C++) |
| `var nome = expr;` | Declaração de variável |
| `nome = expr;` | Atribuição |
| `print(expr, ...);` | Impressão na saída padrão |
| `# comentário` | Comentário de linha |

---
