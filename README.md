# Sistema de Chat Distribuído com Multicast

## Descrição
Este projeto implementa um sistema de chat distribuído utilizando comunicação via UDP multicast. Cada nó (cliente ou servidor) mantém uma réplica local das mensagens em arquivos JSON e adota técnicas de controle de concorrência e tolerância a falhas. As principais funcionalidades são:

- **Comunicação com Multicast:**  
  O servidor e os clientes se comunicam via UDP multicast (ex.: 224.1.1.1:5007).

- **Replicação e Consistência Eventual:**  
  Cada mensagem é gravada na réplica local (por exemplo, `replica_server.json` ou `replica_<UUID>.json`). Um reconciliador no servidor sincroniza periodicamente o histórico com os clientes, garantindo consistência eventual.

- **Exclusão Mútua (Token Ring):**  
  Implementação do algoritmo Token Ring para garantir que apenas um cliente envie mensagens por vez. Após enviar sua mensagem, o cliente libera o token, que é passado para o próximo cliente no anel lógico.

- **Tolerância a Falhas com Checkpoints:**  
  São criados checkpoints periódicos do estado da réplica (tanto no servidor quanto no cliente) para permitir a recuperação em caso de falhas.

- **Execução Concorrente com Threads:**  
  Threads são utilizadas para o envio, recebimento de mensagens e criação de checkpoints, com sincronização via `threading.Lock`.

- **Simulação de Delays Artificiais:**  
  Foram inseridos delays artificiais (entre 100ms e 1 segundo) para simular variações de latência e entregas fora de ordem, permitindo testar a robustez do sistema.

## Tecnologias Utilizadas
- **Linguagem:** Python 3  
- **Bibliotecas:** `socket`, `json`, `os`, `time`, `random`, `threading`, `uuid`, `unittest`, `mock`

## Pré-requisitos
1. Ter o Python 3 instalado.
2. Instalar as dependências listadas em `requirement.txt`:
   ```sh
   pip install -r requirement.txt
   ```

## Como Executar
1. **Servidor:**
   - Inicie o servidor executando:
     ```sh
     python server.py
     ```
   - O servidor ficará escutando no endereço multicast, gravará as mensagens em `replica_server.json`, criará checkpoints e, a cada 10 segundos, sincronizará as réplicas com os clientes.

2. **Clientes:**
   - Em terminais diferentes, execute cada cliente:
     ```sh
     python client.py
     ```
   - Cada cliente gera um UUID único, grava suas mensagens em `replica_<UUID>.json` e cria checkpoints em `checkpoint_<UUID>.json`. Antes de iniciar, os clientes verificam o servidor (através de um "ping") e só enviam mensagens se possuírem o token, que é passado via o algoritmo Token Ring.

3. **Testes Unitários:**
   - Para executar os testes:
     ```sh
     python -m unittest test_client.py
     ```

## Observações
- Toda a documentação deste projeto segue as melhores práticas, enquanto as implementações foram ajustadas para aderir ao PEP‑8 e padrões de qualidade.

## Critérios de Avaliação
| Critério                                                            | Peso |
| ------------------------------------------------------------------- | ---- |
| Funcionamento correto dos módulos e integração entre eles           | 1.5  |
| Clareza, organização e comentários no código                        | 0.5  |
| Demonstração prática (prints, vídeos ou evidências funcionais)        | 0.5  |
| Qualidade da implementação dos conceitos de replicação e recuperação  | 0.5  |

## Entrega
- **Data limite:** 02/04/2025  
- **Forma de envio:** Email para felipe_silva@ifba.edu.br com identificação do aluno, disciplina e turma.