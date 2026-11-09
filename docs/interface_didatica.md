# Interface didática do MiniPar 2026.2

O servidor Flask oferece a interface didática em `/` e `/didatico` e preserva a
IDE do desenvolvedor em `/ide`. O terminal continua disponível pelo menu de
`python main.py` e pela compilação direta de arquivos `.minipar`.

## Instalação e abertura

```powershell
python -m pip install -r requirements.txt -r requirements-dev.txt
python app.py
```

Acesse `http://127.0.0.1:5000/`. É necessário ter g++ com suporte a C++20 no PATH
para executar programas ou baixar executáveis. A análise por fases apenas gera
texto e não invoca g++. D3 e CodeMirror estão em `static/vendor`, com suas licenças,
para que as duas interfaces funcionem sem acesso a CDNs.

## Análise das fases

Digite um programa ou escolha um exemplo e use **Analisar Agora**. Ao editar o
código, os resultados anteriores são invalidados. Uma resposta de análise de
uma versão anterior do texto não substitui os resultados do código atualizado.

| Opção | Resultado |
|---|---|
| Tokens | Tipo, lexema, linha e coluna; busca e filtros por categoria |
| AST | Árvore horizontal com nós recolhíveis, zoom, ajuste e alternativa JSON |
| Semântica | Estado executado/válido/inválido, diagnósticos e símbolos com posição |
| TAC | Texto produzido pelo componente de código intermediário |
| C++ | Código gerado em memória pelo componente `ICodegen/C_Codegen` |

Árvores maiores começam parcialmente recolhidas. Clique em um nó para abrir ou
fechar seus filhos; **Expandir Tudo** abre todos os nós, e **Ajustar** enquadra os
nós visíveis. Os textos completos estão nas dicas dos nós e na alternativa JSON.

Erros léxicos ou sintáticos deixam a semântica como **não executada**. Erros
semânticos impedem TAC e C++. Falhas de geração C++ são diagnósticos de fase
`codegen`, preservando AST, símbolos e TAC já produzidos. A mensagem no editor
informa linha e coluna quando disponíveis. Literais são exibidos como texto,
inclusive quando contêm caracteres que lembram HTML.

## Entrada e execução

Abra **Terminal & Execução** e informe **uma resposta por linha**. Uma resposta
pode conter espaços ou vírgulas; uma linha vazia também é uma resposta válida.
Isso preserva expressões como `((10 -8*7)+4)*2` no Teste 11.

**Executar** compila o programa e executa o binário no servidor local. A interface
didática mostra a saída do programa e o tempo total da requisição, que também
inclui a compilação. Um código de saída diferente de zero é apresentado como
falha. Não se trata de um terminal interativo: forneça as respostas antes de
executar. A execução tem limite de 60 segundos.

Cada requisição compila em um diretório temporário próprio dentro de
`output/web_jobs`. Os arquivos temporários são removidos ao terminar a resposta.
O programa é executado com o diretório do projeto como diretório de trabalho,
preservando caminhos como `output/tapete_sierpinski.bmp` usados pelos exemplos.
Imagens e outros arquivos escritos pelo programa nesse diretório permanecem
disponíveis após o término. Isso não implementa despacho remoto de `fork host`.

## Download do executável

**Baixar .exe** compila sem executar e oferece o binário como anexo. No Windows,
o nome termina em `.exe`; no Linux, a resposta usa o nome nativo sem essa extensão.
O executável corresponde ao sistema em que o servidor está rodando; não há
compilação cruzada. Uma compilação com erro não devolve um binário antigo.

## IDE antiga e terminal

A IDE em `/ide` mantém editor, lista de exemplos, saída C++, TAC e execução.
Ela utiliza a mesma API `/api/compile`, que preserva os campos usados pela
interface anterior. Os controles de redimensionamento de C também foram mantidos.

No terminal, a compilação direta continua sendo:

```powershell
python main.py tests/teste11_tokenizador.minipar
```

Ela grava C++, TAC e executável em `output/`. O arquivo
`tests/inputs/teste11_tokenizador.in` contém uma entrada de referência.

## Validação da integração

```powershell
python -m pytest tests -q
python tests/run_all.py
```

Os nove casos de `tests/test_web.py` verificam as rotas das duas interfaces,
arquivos locais, resultados por fase, erros de geração, entradas com espaços,
download de um executável que realmente roda, falha em execução e requisições
inválidas. São verificações da integração Web, complementares aos programas
solicitados pelo professor. Os casos com compilação exigem g++.

O Teste 10 abre o visualizador de imagens por decisão do próprio programa de
exemplo. Nos ensaios automatizados desta integração, apenas essa abertura foi
desativada em uma cópia do C++ gerado; o programa MiniPar original foi preservado.
