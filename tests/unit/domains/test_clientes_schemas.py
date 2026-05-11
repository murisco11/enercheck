import pytest
from pydantic import ValidationError

from src.app.core.enums import Grupo, ModalidadeTarifaria, Subgrupo
from src.app.domains.clientes.schemas import (
    ClienteCreate,
    DistribuidoraCreate,
    LoteCreate,
    UnidadeConsumidoraCreate,
)


class TestCNPJValidation:
    def test_cnpj_limpo_valido(self):
        c = ClienteCreate(razao_social="Test", cnpj="12345678000199")
        assert c.cnpj == "12345678000199"

    def test_cnpj_com_mascara_valido(self):
        c = ClienteCreate(razao_social="Test", cnpj="12.345.678/0001-99")
        assert c.cnpj == "12345678000199"

    def test_cnpj_curto_invalido(self):
        with pytest.raises(ValidationError, match="14 dígitos"):
            ClienteCreate(razao_social="Test", cnpj="1234567890")

    def test_cnpj_longo_invalido(self):
        with pytest.raises(ValidationError, match="14 dígitos"):
            ClienteCreate(razao_social="Test", cnpj="123456789012345")

    def test_cnpj_distribuidora_com_mascara(self):
        d = DistribuidoraCreate(razao_social="Dist", cnpj="11.222.333/0001-81", sigla="DST", estado="SP")
        assert d.cnpj == "11222333000181"


class TestGrupoSubgrupoValidation:
    def test_grupo_a_subgrupo_valido(self):
        uc = UnidadeConsumidoraCreate(
            distribuidora_id="00000000-0000-0000-0000-000000000001",
            codigo_instalacao="INST001",
            grupo=Grupo.A,
            subgrupo=Subgrupo.A4,
            modalidade=ModalidadeTarifaria.VERDE,
            cidade="São Paulo",
            estado="SP",
        )
        assert uc.grupo == Grupo.A

    def test_grupo_b_subgrupo_valido(self):
        uc = UnidadeConsumidoraCreate(
            distribuidora_id="00000000-0000-0000-0000-000000000001",
            codigo_instalacao="INST002",
            grupo=Grupo.B,
            subgrupo=Subgrupo.B1,
            modalidade=ModalidadeTarifaria.CONVENCIONAL,
            cidade="Rio de Janeiro",
            estado="RJ",
        )
        assert uc.grupo == Grupo.B

    def test_grupo_a_com_subgrupo_b_invalido(self):
        with pytest.raises(ValidationError, match="incompatível com Grupo A"):
            UnidadeConsumidoraCreate(
                distribuidora_id="00000000-0000-0000-0000-000000000001",
                codigo_instalacao="INST003",
                grupo=Grupo.A,
                subgrupo=Subgrupo.B1,
                modalidade=ModalidadeTarifaria.AZUL,
                cidade="São Paulo",
                estado="SP",
            )

    def test_grupo_b_com_subgrupo_a_invalido(self):
        with pytest.raises(ValidationError, match="incompatível com Grupo B"):
            UnidadeConsumidoraCreate(
                distribuidora_id="00000000-0000-0000-0000-000000000001",
                codigo_instalacao="INST004",
                grupo=Grupo.B,
                subgrupo=Subgrupo.A1,
                modalidade=ModalidadeTarifaria.BRANCA,
                cidade="Curitiba",
                estado="PR",
            )

    def test_estado_uppercased(self):
        uc = UnidadeConsumidoraCreate(
            distribuidora_id="00000000-0000-0000-0000-000000000001",
            codigo_instalacao="INST005",
            grupo=Grupo.A,
            subgrupo=Subgrupo.A3a,
            modalidade=ModalidadeTarifaria.AZUL,
            cidade="Belo Horizonte",
            estado="mg",
        )
        assert uc.estado == "MG"


class TestLoteValidation:
    def test_competencias_validas(self):
        from datetime import date

        l = LoteCreate(
            unidade_consumidora_id="00000000-0000-0000-0000-000000000002",
            rotulo="Lote Jan-Mar/2025",
            competencia_inicio=date(2025, 1, 1),
            competencia_fim=date(2025, 3, 31),
        )
        assert l.competencia_inicio < l.competencia_fim

    def test_competencias_mesmo_mes_valido(self):
        from datetime import date

        l = LoteCreate(
            unidade_consumidora_id="00000000-0000-0000-0000-000000000002",
            rotulo="Lote Jan/2025",
            competencia_inicio=date(2025, 1, 1),
            competencia_fim=date(2025, 1, 1),
        )
        assert l.competencia_inicio == l.competencia_fim

    def test_competencia_fim_anterior_ao_inicio_invalido(self):
        from datetime import date

        with pytest.raises(ValidationError, match="competencia_fim"):
            LoteCreate(
                unidade_consumidora_id="00000000-0000-0000-0000-000000000002",
                rotulo="Lote inválido",
                competencia_inicio=date(2025, 3, 1),
                competencia_fim=date(2025, 1, 1),
            )
