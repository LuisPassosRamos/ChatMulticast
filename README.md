# Chat distribuído com UDP multicast

Exercício de Sistemas Distribuídos em Python. Um servidor coordena clientes automatizados que trocam mensagens num grupo multicast. O objetivo é observar como um token dá a vez de enviar, como cada nó guarda uma réplica e como um checkpoint local registra o último estado conhecido.

## Executar

Com Docker e o plugin Docker Compose instalados, abra um terminal na raiz do projeto.

```bash
docker compose up --build --scale client=3
```

Nos logs, procure a entrada de cada cliente, a circulação do token e a gravação das mensagens. A execução padrão usa cinco clientes. Com `python main.py`, os contêineres iniciam em segundo plano e o terminal acompanha os logs. Encerre a demonstração com `docker compose down`.

Para executar sem Docker, use `python server.py` e abra terminais adicionais com `python client.py` em uma rede que suporte multicast UDP. A aplicação usa apenas a biblioteca padrão.

## O que observar no código

| Conceito | Onde aparece |
| --- | --- |
| Multicast UDP | [Servidor](server.py) e [clientes](client.py) usam o grupo `224.1.1.1:50007`. |
| Exclusão mútua | O servidor distribui o token e cada cliente usa a lista de vizinhos para passar a vez. |
| Réplica e recuperação | Cada nó armazena mensagens e checkpoints em JSON. O servidor envia seu histórico periodicamente para reconciliar as cópias. |

A demonstração usa atrasos artificiais. UDP admite perdas, duplicatas e entregas fora de ordem. A coordenação depende do servidor e os arquivos dentro dos contêineres permanecem disponíveis enquanto esses contêineres existirem. O exercício é reproduzível em uma rede local com multicast habilitado.

Os [testes do servidor](tests/test_server.py) verificam a passagem do token com gravação do checkpoint e o descarte de uma mensagem repetida. Execute com `python -m unittest discover -s tests`.
