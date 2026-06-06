"""DSL declarativa das regras de validação (armazenada em RegraValidacao.expressao_logica).

A regra é um JSON com um `tipo` e seus parâmetros. O motor é determinístico: a IA
não participa da avaliação. Tipos suportados nesta versão:

- ``recalculo_consumo``: confere se o consumo medido confere com
  (leitura_atual − leitura_anterior) × constante, por medida.
- ``valor_item_por_tarifa``: confere se o valor dos itens de um tipo confere com
  quantidade × tarifa do snapshot (``campo_snapshot``).
- ``soma_itens_total``: confere se a soma dos itens confere com o valor total.

Exemplo::

    {"tipo": "valor_item_por_tarifa", "tipo_item": "tusd",
     "campo_snapshot": "valor_tusd_com_tributos", "tolerancia": "0.50"}
"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.app.core.enums import TipoItem

TipoRegra = Literal["recalculo_consumo", "valor_item_por_tarifa", "soma_itens_total"]


class RegraDSL(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: TipoRegra
    tolerancia: Decimal = Decimal("0.01")
    tipo_item: TipoItem | None = None
    campo_snapshot: str | None = None
    descricao_saida: str | None = None
