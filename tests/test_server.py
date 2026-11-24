import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import server


class ServerTests(unittest.TestCase):
    def test_token_is_sent_and_checkpointed(self):
        with TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            socket = Mock()
            with (
                patch.object(server, "NEIGHBORS", {"client"}),
                patch.object(server, "token_holder", server.SERVER_ID),
                patch.object(server, "CHECKPOINT_SERVER_FILE", checkpoint),
            ):
                worker = threading.Thread(target=server.enviar_token, args=(socket,), daemon=True)
                worker.start()
                worker.join(timeout=2)
                self.assertFalse(worker.is_alive(), "O token e o checkpoint disputam o mesmo lock")
                self.assertEqual(server.token_holder, "client")
                self.assertFalse(json.loads(checkpoint.read_text())["token"])
                socket.sendto.assert_called_once()

    def test_duplicate_message_is_recorded_once(self):
        with TemporaryDirectory() as directory:
            replica = Path(directory) / "replica.json"
            replica.write_text("[]")
            with patch.object(server, "REPLICA_SERVER_FILE", replica):
                entry = {"type": "chat", "sender": "client", "timestamp": 10}
                server.gravar_mensagem(entry)
                server.gravar_mensagem(entry)
            self.assertEqual(json.loads(replica.read_text()), [entry])
