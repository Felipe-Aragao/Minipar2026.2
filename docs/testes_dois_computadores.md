# Testes MiniPar em dois computadores

Os programas de `tests/distribuidos/` são variantes dos testes 1 e 2 com os papéis
separados por máquina. Eles usam os canais TCP do runtime real do MiniPar.
Não substituem os 11 programas oficiais nem implementam despacho remoto automático
de `fork host(...)`.

## Preparação

1. Usar a mesma versão do projeto nos dois PCs, com Python e g++ com C++20 disponíveis.
2. Preferir os dois computadores na mesma rede local. Em locais diferentes, é
   necessário um caminho de rede alcançável, por exemplo uma VPN privada entre os PCs.
   Estar na mesma chamada de vídeo ou acessar o mesmo GitHub não conecta os canais.
3. Conferir o IPv4 da interface usada para essa rede: `ipconfig` no Windows ou
   `ip address` no Linux. Não usar `127.0.0.1` nos ensaios físicos.
4. Permitir somente as portas TCP necessárias no firewall, conforme as permissões
   da rede. Não é necessário desativar o firewall nem publicar portas na internet.
   Redes Wi-Fi de convidados podem bloquear a comunicação entre dispositivos.

| Teste | PC A recebe | PC B recebe |
|---|---|---|
| 1 - calculadora | TCP 15102 | TCP 15101, 15103 e 15104 |
| 2 - fatorial/Fibonacci | TCP 15202 | TCP 15201 |

Os dois PCs precisam aceitar conexões, pois o resultado volta por um canal próprio.
O runtime recebe em todas as interfaces IPv4; a regra de firewall deve restringir
o acesso ao outro PC ou à rede privada do laboratório.

## Teste 1 - calculadora

Exemplo de endereços: PC A `192.168.1.10`, PC B `192.168.1.20`.
Substituir pelos IPs reais. Executar os comandos na raiz do projeto.

Primeiro, no **PC B**:

```powershell
python tests/distribuidos/executar.py --teste 1 --papel b --ip-par 192.168.1.10
```

Após aparecer `Executando`, iniciar no **PC A**:

```powershell
python tests/distribuidos/executar.py --teste 1 --papel a --ip-par 192.168.1.20
```

O PC A envia `+`, `7` e `5`. O PC B calcula `12` e devolve a resposta.
Os dois terminais devem terminar com `PASSOU`.

## Teste 2 - fatorial/Fibonacci

Primeiro, no **PC B**:

```powershell
python tests/distribuidos/executar.py --teste 2 --papel b --ip-par 192.168.1.10
```

Após aparecer `Executando`, iniciar no **PC A**:

```powershell
python tests/distribuidos/executar.py --teste 2 --papel a --ip-par 192.168.1.20
```

O PC A possui duas tarefas locais: uma calcula `5! = 120`; a outra solicita ao
PC B a sequência de Fibonacci com oito termos e recebe `0 1 1 2 3 5 8 13`.
O PC B calcula essa sequência e envia o resultado. A ordem das mensagens pode variar.
As tarefas permitem concorrência; o cálculo pequeno não demonstra ganho de desempenho
nem garante sobreposição temporal observável em todas as execuções.

## Evidências para o professor

Cada execução grava um JSON em `output/testes_distribuidos/`, com data UTC, nome da
máquina, sistema, Python, IP do par, saídas, retorno e checagem do resultado.
Guardar os arquivos dos dois PCs e capturas com `ipconfig`/`ip address` e os terminais
da execução. Registrar também `git rev-parse HEAD` nos dois computadores.
O modo `rede` no JSON indica o modo solicitado ao executor; os logs e capturas dos
dois hosts são necessários para comprovar que foram máquinas diferentes.

## Ensaio local

```powershell
python tests/distribuidos/executar.py --teste 1 --local
python tests/distribuidos/executar.py --teste 2 --local
```

Esse modo compila e executa os dois papéis em processos separados usando loopback,
verifica as respostas e identifica o resultado como local. Não comprova dois PCs.

## Problemas comuns

- `g++` não encontrado: configurar o compilador no PATH antes de executar.
- Timeout: conferir IPs, portas, firewall e isolamento da rede Wi-Fi; iniciar B
  primeiro. A compilação de A deve terminar enquanto B ainda aguarda (90 segundos).
- Se demorar para preparar A, executar uma vez localmente em cada PC para conferir
  o ambiente e depois repetir os comandos de rede próximos no tempo.
- Executar um par de cada vez: cada programa processa uma requisição e termina.
- A rede pode falhar mesmo com a compilação correta; o executor retorna erro e
  não converte falha de conexão em resultado aprovado.

## Escopo que continua pendente

`fork host(...)` ainda avisa e executa localmente. Nestes ensaios, cada usuário
inicia explicitamente um programa na sua máquina, e os programas se comunicam por
mensagens TCP. Isso valida os exemplos distribuídos, não o envio automático de
um bloco MiniPar arbitrário para execução remota.
