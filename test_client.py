import unittest
import json
import os
from unittest.mock import patch, MagicMock
from client import gravar_mensagem, sincronizar_replicas, receber_mensagens, enviar_mensagens, carregar_checkpoint, salvar_checkpoint

class TestClientFunctions(unittest.TestCase):

    def setUp(self):
        self.replica_file = "replica.json"
        self.checkpoint_file = "checkpoint.json"

        with open(self.replica_file, "w") as f:
            json.dump([], f)
        with open(self.checkpoint_file, "w") as f:
            json.dump({"last_message": "", "token": False, "neighbors": []}, f)

    def tearDown(self):
        if os.path.exists(self.replica_file):
            os.remove(self.replica_file)
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)

    def test_gravar_mensagem(self):
        mensagem = "Teste de mensagem"
        gravar_mensagem(mensagem)

        with open(self.replica_file, "r") as f:
            historico = json.load(f)

        self.assertIn(mensagem, historico)

    def test_sincronizar_replicas(self):
        mensagens = ["Mensagem 3", "Mensagem 1", "Mensagem 2"]
        with open(self.replica_file, "w") as f:
            json.dump(mensagens, f)

        sincronizar_replicas()

        with open(self.replica_file, "r") as f:
            historico = json.load(f)

        self.assertEqual(historico, sorted(mensagens))

    def test_carregar_checkpoint(self):
        checkpoint_data = {"last_message": "Teste", "token": True, "neighbors": ["127.0.0.1"]}
        salvar_checkpoint(**checkpoint_data)

        loaded_data = carregar_checkpoint()
        self.assertEqual(loaded_data, checkpoint_data)

    @patch("socket.socket.recvfrom")
    def test_receber_mensagens_sincronizacao(self, mock_recvfrom):
        # Simula mensagens fora de ordem
        mock_recvfrom.side_effect = [
            (b"Mensagem 3", ("127.0.0.1", 5007)),
            (b"Mensagem 1", ("127.0.0.1", 5007)),
            (b"Mensagem 2", ("127.0.0.1", 5007)),
        ]

        # Recebe as mensagens
        for _ in range(3):
            receber_mensagens()

        # Verifica se as mensagens foram sincronizadas na ordem correta
        with open(self.replica_file, "r") as f:
            historico = json.load(f)

        self.assertEqual(historico, ["Mensagem 1", "Mensagem 2", "Mensagem 3"])

    @patch("socket.socket.recvfrom")
    def test_receber_mensagens_com_atraso(self, mock_recvfrom):
        # Simula mensagens com atraso
        def delayed_messages(*args, **kwargs):
            import time
            time.sleep(1)  # Simula atraso de 1 segundo
            return (b"Mensagem atrasada", ("127.0.0.1", 5007))

        mock_recvfrom.side_effect = delayed_messages

        # Recebe a mensagem com atraso
        receber_mensagens()

        # Verifica se a mensagem foi gravada corretamente
        with open(self.replica_file, "r") as f:
            historico = json.load(f)

        self.assertIn("Mensagem atrasada", historico)

    @patch("socket.socket.recvfrom")
    def test_receber_mensagens_simultaneas(self, mock_recvfrom):
        # Simula mensagens de dois clientes diferentes
        mock_recvfrom.side_effect = [
            (b"Mensagem Cliente 1", ("127.0.0.1", 5007)),
            (b"Mensagem Cliente 2", ("127.0.0.2", 5007)),
        ]

        # Recebe as mensagens
        for _ in range(2):
            receber_mensagens()

        # Verifica se ambas as mensagens foram gravadas
        with open(self.replica_file, "r") as f:
            historico = json.load(f)

        self.assertIn("Mensagem Cliente 1", historico)
        self.assertIn("Mensagem Cliente 2", historico)

    def test_token_behavior(self):
        checkpoint_data = {"last_message": "Teste", "token": True, "neighbors": []}
        salvar_checkpoint(**checkpoint_data)

        # Simula o envio de uma mensagem
        enviar_mensagens()

        # Verifica se o token foi liberado
        checkpoint = carregar_checkpoint()
        self.assertFalse(checkpoint["token"], "O token não foi liberado corretamente após o envio da mensagem.")


if __name__ == "__main__":
    unittest.main()