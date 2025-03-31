# Sistema de Chat Distribuído com Multicast

## Descrição
Este projeto tem como objetivo desenvolver um sistema de chat em grupo distribuído, utilizando comunicação via multicast, replicação de mensagens, controle de concorrência e tolerância a falhas. O projeto faz parte da disciplina de Sistemas Distribuídos do Instituto Federal de Educação, Ciência e Tecnologia da Bahia.

## Objetivos
1. **Comunicação em Grupo com Multicast**
   - Implementar comunicação utilizando sockets com protocolo UDP multicast.
   - Criar um servidor e clientes que se comuniquem via multicast IP (exemplo: 224.1.1.1:5007).
   - Garantir que os clientes possam enviar e receber mensagens de todos os participantes.

2. **Replicação de Dados e Consistência Eventual**
   - Gravar cada mensagem recebida em arquivos locais (réplicas) no formato JSON.
   - Incluir um delay artificial para simular entrega fora de ordem.
   - Criar um processo reconciliador para sincronizar os dados entre as réplicas.

3. **Controle de Concorrência com Exclusão Mútua Distribuída**
   - Implementar um algoritmo de exclusão mútua (Token Ring).
   - Garantir que apenas um nó por vez envie mensagens ao grupo.
   - Exibir mensagens de requisição e concessão de acesso ao recurso via token.

4. **Tolerância a Falhas com Checkpoints e Rollback**
   - Criar snapshots do estado do cliente periodicamente em arquivos JSON.
   - Restaurar o estado salvo no último checkpoint após uma falha.
   - Utilizar arquivos simples ou SQLite para armazenar checkpoints (neste exemplo, JSON).

## Tecnologias Utilizadas
- **Linguagem**: Python 3
- **Bibliotecas**:
  - `socket` (para comunicação via UDP multicast)
  - `time` e `random` (para simular delays na entrega de mensagens)
  - `json` (para armazenamento de mensagens e checkpoints)
  - `threading` ou `asyncio` (opcional, para controle concorrente)

## Como Executar
1. **Executar o Servidor**
   - Rode o seguinte comando na pasta raiz:
     ```sh
     python server.py
     ```
   - O servidor ficará escutando mensagens no endereço multicast (224.1.1.1:5007).

2. **Executar os Clientes**
   - Rode o seguinte comando para cada cliente em terminais diferentes:
     ```sh
     python client.py
     ```
   - Cada cliente criará ou usará réplicas (`replica.json`) e checkpoints (`checkpoint.json`).

3. **Testes e Demonstração**
   - O sistema deve ser testado com pelo menos 3 clientes conectados simultaneamente.
   - Registre prints ou vídeos da execução para documentação.

## Critérios de Avaliação
| Critério | Peso |
|-----------|------|
| Funcionamento correto dos módulos e integração entre eles | 1.5 |
| Clareza, organização e comentários no código | 0.5 |
| Demonstração prática (prints, vídeos ou evidência funcional) | 0.5 |
| Qualidade da implementação dos conceitos de replicação e recuperação | 0.5 |

## Entrega
- **Data limite:** 02/04/2025  
- **Forma de envio:** Email para felipe_silva@ifba.edu.br com identificação do aluno, disciplina e turma.