"""Inicia o laboratório e acompanha os logs pelo Docker Compose."""

import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    try:
        subprocess.run(["docker", "compose", "up", "--build", "-d"], cwd=root, check=True)
        return subprocess.run(["docker", "compose", "logs", "-f"], cwd=root).returncode
    except FileNotFoundError:
        print("Instale o Docker com o plugin Compose para executar a demonstração.")
        return 1
    except subprocess.CalledProcessError as error:
        return error.returncode
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
