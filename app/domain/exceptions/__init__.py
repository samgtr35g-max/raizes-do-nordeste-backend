class ErroDeDominio(Exception):
    """Base para os erros de dominio do sistema."""

    status = 400
    codigo = "erro_de_dominio"

    def __init__(self, mensagem="Erro de dominio."):
        super().__init__(mensagem)
        self.mensagem = mensagem


class ValidacaoError(ErroDeDominio):
    """Dados de entrada invalidos."""

    status = 422
    codigo = "dados_invalidos"

    def __init__(self, mensagem="Dados invalidos."):
        super().__init__(mensagem)


class RecursoNaoEncontradoError(ErroDeDominio):
    """Recurso inexistente."""

    status = 404
    codigo = "nao_encontrado"

    def __init__(self, mensagem="Recurso nao encontrado."):
        super().__init__(mensagem)


class AcessoNegadoError(ErroDeDominio):
    """Usuario sem autorizacao para o recurso/escopo solicitado."""

    status = 403
    codigo = "acesso_negado"

    def __init__(self, mensagem="Acesso negado."):
        super().__init__(mensagem)


class EstoqueInsuficienteError(ErroDeDominio):
    """Operacao deixaria o estoque negativo."""

    status = 409
    codigo = "estoque_insuficiente"

    def __init__(self, mensagem="Estoque insuficiente."):
        super().__init__(mensagem)


class TransicaoStatusInvalidaError(ErroDeDominio):
    """Transicao de status de pedido nao permitida."""

    status = 409
    codigo = "transicao_invalida"

    def __init__(self, mensagem="Transicao de status invalida."):
        super().__init__(mensagem)


class PagamentoNaoPermitidoError(ErroDeDominio):
    """Pagamento nao permitido para o pedido no estado atual."""

    status = 409
    codigo = "pagamento_nao_permitido"

    def __init__(self, mensagem="Pagamento nao permitido para este pedido."):
        super().__init__(mensagem)


class PagamentoDuplicadoError(ErroDeDominio):
    """Pedido ja possui um pagamento aprovado."""

    status = 409
    codigo = "pagamento_duplicado"

    def __init__(self, mensagem="Pedido ja possui pagamento aprovado."):
        super().__init__(mensagem)


class SaldoInsuficienteError(ErroDeDominio):
    """Saldo de pontos insuficiente para o resgate."""

    status = 409
    codigo = "saldo_insuficiente"

    def __init__(self, mensagem="Saldo de pontos insuficiente."):
        super().__init__(mensagem)


class CredenciaisInvalidasError(ErroDeDominio):
    """Email inexistente ou senha incorreta."""

    status = 401
    codigo = "credenciais_invalidas"

    def __init__(self, mensagem="Email ou senha invalidos."):
        super().__init__(mensagem)


class UsuarioInativoError(ErroDeDominio):
    """Usuario existe, mas esta inativo."""

    status = 403
    codigo = "usuario_inativo"

    def __init__(self, mensagem="Usuario inativo."):
        super().__init__(mensagem)
