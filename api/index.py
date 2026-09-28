"""
Ponto de entrada da Vercel.

Por que este arquivo existe:
    A Vercel procura as funções serverless dentro de uma pasta chamada "api/".
    Ela olha para o arquivo api/index.py, encontra a variável "app" aqui dentro
    e usa isso para responder às visitas do site.

O que ele faz:
    Nada além de importar a aplicação que está no app.py, lá na pasta de cima.
    Toda a lógica continua no app.py - este arquivo é só a "porta de entrada".
"""

import os
import sys

# Coloca a pasta de cima (a raiz do projeto, onde está o app.py) na lista de
# lugares onde o Python procura arquivos para importar.
PASTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PASTA_RAIZ)

# É esta variável "app" que a Vercel procura.
from app import app  # noqa: E402
