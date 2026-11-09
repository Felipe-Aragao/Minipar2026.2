# Pseudocódigos do front-end do compilador MiniPar 2026.2

Érico Almeida Bernardino · Felipe Lima Aragão · Lucas Trindade de Souza

Este documento apresenta os pseudocódigos dos itens 3 a 6 do relatório do projeto:
análise léxica, análise sintática, análise semântica e tabela de símbolos. Os
algoritmos descrevem a implementação Python, inclusive suas limitações. A notação
é descritiva; os blocos abaixo não são programas executáveis em MiniPar.

O percurso do front-end é código fonte → tokens → AST → validação semântica → TAC.
Uma fase com erro impede a geração das fases seguintes. A API preserva os dados
das fases concluídas e apresenta diagnósticos com fase, linha, coluna e mensagem.

## 3 Analisador léxico

Implementação: `src/lexer.py`. Interface e componente: `ILexico` e `C_Lexico`.
Entrada: código fonte. Saída: lista de tokens, incluindo `END_OF_FILE`.

Cada token contém tipo, lexema, linha e coluna. A posição inicial é linha 1,
coluna 1. Ao consumir uma quebra de linha, a linha aumenta e a coluna volta a 1;
os demais caracteres, inclusive tabulações, aumentam a coluna em uma unidade.

```text
ALGORITMO ANALISE_LEXICA(codigo)
    posicao ← 0; linha ← 1; coluna ← 1
    tokens ← lista vazia
    ENQUANTO houver caracteres
        CONSUMIR espaços em branco
        SE o próximo caractere for '#'
            CONSUMIR até quebra de linha ou fim do código
            CONTINUAR
        SE chegou ao fim: INTERROMPER
        inicio ← (linha, coluna)

        SE começa com letra ou '_'
            lexema ← CONSUMIR letras, dígitos e '_'
            tipo ← CONSULTAR lexema no mapa de palavras reservadas
            SE não encontrado: tipo ← IDENTIFIER
            ADICIONAR TOKEN(tipo, lexema, inicio)
        SENÃO SE começa com dígito
            lexema ← CONSUMIR dígitos
            SE o próximo caractere for '.'
                CONSUMIR '.' e os dígitos seguintes, se existirem
            ADICIONAR TOKEN(NUMBER, lexema, inicio)
        SENÃO SE começa com aspas duplas
            CONSUMIR aspas de abertura; texto ← vazio
            ENQUANTO não chegar às aspas finais nem ao fim do código
                SE encontrar barra invertida
                    CONSUMIR barra e caractere seguinte
                    CONVERTER escapes n, t, aspas e barra invertida
                    PARA outros escapes, manter o caractere após a barra
                SENÃO: ACRESCENTAR caractere consumido ao texto
            SE não encontrou aspas finais
                LANÇAR LexError("String nao terminada", inicio)
            CONSUMIR aspas finais
            ADICIONAR TOKEN(STRING_LITERAL, texto, inicio)
        SENÃO
            CONSUMIR operador ou delimitador
            PRIORIZAR ==, !=, &&, ||, <= e >= quando aplicável
            SE reconhecido: ADICIONAR token correspondente
            SENÃO: ADICIONAR TOKEN(UNKNOWN, caractere, inicio)
    ADICIONAR TOKEN(END_OF_FILE, "", linha, coluna)
    RETORNAR tokens
FIM
```

Comentários `#` são descartados fora de strings e podem terminar no fim do
arquivo. O lexer entrega caracteres desconhecidos como `UNKNOWN`; a API e o
terminal identificam esses tokens e interrompem o fluxo antes do parser.
`C_Lexico` cria um lexer novo a cada chamada.

## 4 Analisador sintático

Implementação: `src/parser.py`, com nós definidos em `src/ast_nodes.py`.
Interface e componente: `ISintatico` e `C_Sintatico`. Entrada: tokens.
Saída: AST cuja raiz é `Program`, ou erro sintático com posição.

O parser é descendente recursivo. Um procedimento reconhece cada construção e
consome os tokens esperados. Os nós registram linha e coluna do token associado,
como o nome de uma variável, operador, chamada ou palavra que inicia um comando.

```text
ALGORITMO ANALISE_SINTATICA(tokens)
    posicao ← 0
    programa ← novo nó Program na posição do primeiro token
    ENQUANTO token atual não for END_OF_FILE
        comando ← ANALISAR_COMANDO()
        SE comando existir: ADICIONAR comando ao programa
    RETORNAR programa
FIM

PROCEDIMENTO CONSUMIR(tipo_esperado)
    SE token atual tiver tipo_esperado
        RETORNAR token atual e AVANÇAR
    SENÃO: LANÇAR ParseError(mensagem, token atual)
FIM

FUNÇÃO ANALISAR_COMANDO()
    ESCOLHER conforme token atual
        var ou tipo: LER nome, inicialização opcional e ';'; CRIAR VarDecl
        func: LER nome, parâmetros e corpo; CRIAR FuncDecl
        class: LER nome, herança opcional, atributos e métodos; CRIAR ClassDecl
        seq ou '{': ANALISAR_BLOCO(SeqBlock)
        par: ANALISAR_BLOCO(ParBlock)
        if, while, do ou for: LER condição, partes e blocos correspondentes
        print, send ou return: LER argumentos/valor e delimitadores exigidos
        break ou continue: EXIGIR ';'; CRIAR nó correspondente
        OUTRO: ANALISAR expressão
            SE seguida de '='
                LER valor e EXIGIR ';'
                CRIAR atribuição a nome, propriedade ou índice
            SENÃO: EXIGIR ';' conforme a forma do comando
    RETORNAR nó construído
FIM

FUNÇÃO ANALISAR_BLOCO(tipo)
    CONSUMIR '{'; bloco ← novo nó do tipo recebido
    ENQUANTO não encontrar '}' nem END_OF_FILE
        ADICIONAR ANALISAR_COMANDO() ao bloco
    CONSUMIR '}'
    RETORNAR bloco
FIM
```

### Expressões e precedência

Os procedimentos reais são `_parse_or`, `_parse_and`, `_parse_comparison`,
`_parse_term`, `_parse_factor`, `_parse_unary` e `_parse_primary`. No código,
`term` corresponde à soma/subtração e `factor` à multiplicação/divisão/resto.
Igualdade e operadores relacionais compartilham o mesmo nível de comparação.

```text
EXPRESSAO    → OU
OU           → combinar E usando '||'
E            → combinar COMPARACAO usando '&&'
COMPARACAO   → combinar SOMA usando '==', '!=', '<', '>', '<=', '>='
SOMA         → combinar PRODUTO usando '+' e '-'
PRODUTO      → combinar UNARIO usando '*', '/' e '%'
UNARIO       → operador '+', '-' ou '!' seguido de UNARIO; ou PRIMARIO
PRIMARIO     → literal, identificador, expressão entre parênteses,
               lista, construção nativa, instanciação, fork ou join
               com acessos, índices e chamadas permitidos pelo parser

PARA cada nível binário
    esquerda ← analisar próximo nível
    ENQUANTO houver operador desse nível
        operador ← consumir token
        direita ← analisar próximo nível
        esquerda ← BinaryExpr(operador, esquerda, direita, posição do operador)
    RETORNAR esquerda
```

`fork` reconhece destino opcional `core(...)` ou `host(...)`, seguido de bloco
ou expressão. `join` reconhece a barreira sem argumentos ou argumentos entre
parênteses. O parser constrói os nós; a validade dos destinos e argumentos é
verificada posteriormente pelo semântico. O ponto e vírgula depende do uso
como comando, inicializador ou expressão, conforme a BNF do projeto.

`C_Sintatico` usa o modo `raise_errors=True`, no qual erros geram `ParseError`
sem encerrar o processo consumidor. O modo antigo do parser ainda pode imprimir
o erro e encerrar o processo. `Program.to_dict()` serializa a AST para a interface.

## 5 Analisador semântico e tratamento de erros

Implementação: `src/semantic.py`. Interface e componente: `ISemantico` e
`C_Semantico`. Entrada: AST. Saída: sucesso, histórico de símbolos e diagnósticos.
O componente cria um analisador novo para cada programa.

```text
ALGORITMO ANALISE_SEMANTICA(programa)
    CRIAR tabela de símbolos com escopo global
    erros ← lista vazia
    contexto de função/classe/tarefa ← vazio
    profundidade de laço ← 0
    PRÉ-COLETAR assinaturas das funções e das classes do nível principal
    PARA cada comando do programa: VALIDAR(comando)
    RETORNAR (erros está vazia, tabela.LISTAR_SIMBOLOS(), erros)
FIM

PROCEDIMENTO VALIDAR(no)
    SE no for ausente: RETORNAR
    ESCOLHER tipo do nó
        DECLARAÇÃO DE VARIÁVEL
            VALIDAR inicialização; INFERIR seu tipo
            CONFERIR compatibilidade com tipo declarado
            PARA var, USAR tipo inferido quando conhecido
            DECLARAR símbolo; REPORTAR duplicata se recusado
        IDENTIFICADOR
            CONSULTAR declaração visível; REPORTAR se inexistente
        ATRIBUIÇÃO
            CONFERIR existência do alvo e isolamento de escrita
            VALIDAR valor; CONFERIR compatibilidade conhecida
        ATRIBUIÇÃO POR ÍNDICE OU PROPRIEDADE
            VALIDAR alvo e valor; LOCALIZAR identificador raiz
            CONFERIR isolamento da raiz e propriedade conhecida, se aplicável
        EXPRESSÃO
            VALIDAR operandos; CONFERIR tipos nas operações verificadas
        BLOCO SEQUENCIAL
            ENTRAR escopo; VALIDAR comandos; SAIR escopo
        FUNÇÃO
            DECLARAR função; ENTRAR escopo e SALVAR contexto anterior
            DECLARAR parâmetros usando suas posições individuais
            VALIDAR corpo; RESTAURAR contexto e SAIR escopo
        CLASSE
            CONFERIR superclasse, se informada
            DECLARAR classe; ENTRAR escopo e SALVAR contexto anterior
            VALIDAR atributos e métodos; RESTAURAR contexto e SAIR escopo
        CONDICIONAL
            VALIDAR condição e ramos
        LAÇO
            VALIDAR partes; GERENCIAR escopo do for, quando aplicável
            AUMENTAR profundidade de laço; VALIDAR corpo; DIMINUIR profundidade
        BREAK OU CONTINUE
            REPORTAR se profundidade de laço for zero
        CHAMADA
            CONFERIR nome e quantidade de argumentos quando conhecidos
            APLICAR regras específicas das nativas e dos métodos
            VALIDAR argumentos e objeto receptor, se houver
        FORK
            VALIDAR destino e argumentos de core/host
            VALIDAR_TAREFA(corpo, "fork")
        PAR
            PARA cada comando: VALIDAR_TAREFA(comando, "par")
        JOIN
            VALIDAR argumentos; REJEITAR listas e tipos conhecidos não task
        OUTROS NÓS SUPORTADOS
            VALIDAR expressões ou comandos filhos correspondentes
FIM
```

### Isolamento de tarefas

```text
PROCEDIMENTO VALIDAR_TAREFA(corpo, tipo)
    SALVAR limite e tipo da tarefa atual
    limite ← quantidade de escopos ativos antes de abrir o escopo da tarefa
    tipo da tarefa ← tipo
    ENTRAR escopo exclusivo da tarefa
    TENTAR: VALIDAR(corpo)
    FINALMENTE
        SAIR escopo exclusivo
        RESTAURAR limite e tipo anteriores
FIM

PROCEDIMENTO CONFERIR_ISOLAMENTO(nome, no)
    SE não estiver numa tarefa paralela: RETORNAR
    indice ← tabela.LOCALIZAR_ESCOPO(nome)
    SE indice existir e indice < limite da tarefa
        REPORTAR(no, "Variavel externa não pode ser alterada nesta tarefa")
FIM
```

A verificação também se aplica a `append`, `push_back` e `pop` de coleções
externas. Cada comando de `par` é uma tarefa: as declarações não vazam para as
tarefas irmãs. Tarefas aninhadas têm limites próprios. Leituras externas são
permitidas. O C++ captura valores, mas objetos `shared_ptr` não recebem cópia
profunda. Não há análise completa de aliases nem de efeitos indiretos de chamadas.

### Regras específicas e diagnósticos

`len` exige um argumento e rejeita tipos conhecidos que não sejam string, lista
ou matriz; tipos desconhecidos permanecem permitidos. `fmt` e `save_bmp` exigem
dois argumentos, e `launch_file` exige um. O reconhecimento de uma nativa não
implica validação completa de todos os seus tipos. `core` exige expressão numérica;
constantes devem ser inteiras e não negativas, com diagnóstico de divisão por
zero na avaliação constante. `host` verifica as formas de canal ou IP/porta,
sem implementar o despacho remoto. `join` rejeita listas e argumentos de tipo
conhecido incompatível com tarefa.

```text
PROCEDIMENTO REPORTAR(no, mensagem)
    ACRESCENTAR contexto da função à mensagem, quando houver
    ADICIONAR {fase: "semantica", linha: no.line,
               coluna: no.col, mensagem: mensagem} à lista de erros
    MARCAR análise como inválida
    SE emissão de diagnósticos estiver habilitada
        IMPRIMIR posição e mensagem na saída de erro
FIM
```

O semântico pode acumular mais de um diagnóstico. Em caso de falha, a API mantém
tokens, AST e símbolos obtidos, mas não produz TAC. Erros de lexer e parser são
tratados antes da validação semântica. Coluna desconhecida em nós legados é `null`.
Esse comportamento descreve as verificações implementadas, não uma prova completa
da correção de tipos, efeitos ou execução de qualquer programa.

## 6 Tabela de símbolos

Implementação: `src/componente_tabela_simbolos.py`. Interface e componente:
`ITabelaSimbolos` e `C_TabelaSimbolos`. O semântico consulta essa interface para
resolver nomes, controlar escopos e exportar dados para a Web.

A estrutura mantém uma pilha de dicionários de símbolos, os identificadores dos
escopos e um histórico das declarações aceitas. Um `Symbol` reúne nome, tipo,
parâmetros e metadados de atributos e métodos. O semântico mantém separadamente
os índices de assinaturas de funções e classes pré-coletadas.

```text
INICIALIZAR_TABELA()
    escopos ← [dicionário vazio]
    ids_ativos ← [0]; proximo_id ← 1
    historico ← lista vazia

ENTRAR_ESCOPO()
    EMPILHAR dicionário vazio em escopos
    EMPILHAR proximo_id em ids_ativos
    proximo_id ← proximo_id + 1

SAIR_ESCOPO()
    SE houver mais de um escopo ativo
        DESEMPILHAR escopos e ids_ativos

DECLARAR(simbolo, linha, coluna, funcao, classe)
    SE simbolo.nome já existir no escopo do topo: RETORNAR falso
    INSERIR simbolo no escopo do topo
    ADICIONAR ao historico:
        nome, tipo, linha, coluna, id do escopo, função, classe,
        cópia da lista de parâmetros
    RETORNAR verdadeiro

LOCALIZAR_ESCOPO(nome)
    PARA indice do topo da pilha até o escopo global
        SE nome existir em escopos[indice]: RETORNAR indice
    RETORNAR ausente

CONSULTAR(nome)
    indice ← LOCALIZAR_ESCOPO(nome)
    SE indice existir: RETORNAR escopos[indice][nome]
    RETORNAR ausente

LISTAR_SIMBOLOS()
    RETORNAR cópias dos registros do historico e de suas listas de parâmetros
```

Uma duplicata não substitui o símbolo original. Um nome em escopo interno pode
ocultar um nome externo; ao sair desse escopo, a declaração externa volta a ser
encontrada. O histórico não é apagado ao encerrar um escopo, e seus identificadores
não são reutilizados. O índice de escopo ativo usado no isolamento é diferente
do identificador persistente exportado no histórico.
