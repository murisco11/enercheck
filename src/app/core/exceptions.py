class IntegrationError(Exception):
    """Erro de integração com sistemas externos."""


class NaoEncontradoError(Exception):
    """Recurso não encontrado no banco."""


class ConflitoDuplicidadeError(Exception):
    """Registro duplicado (violação de unique constraint)."""


class RegraVioladaError(Exception):
    """Regra de negócio violada."""


class AcessoNegadoError(Exception):
    """Usuário sem permissão para a operação."""


class CredenciaisInvalidasError(Exception):
    """Credenciais de autenticação inválidas."""


class ExtracacaoError(Exception):
    """Falha na extração de dados do documento."""
