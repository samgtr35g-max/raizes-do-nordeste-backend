from app.domain.exceptions import AcessoNegadoError, ValidacaoError


def id_opcional(valor, campo):
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValidacaoError(f"{campo} invalido.")
    return valor


def resolver_unidade(usuario, unidade_informada, obrigatorio):
    if usuario.unidadeId is not None:
        if unidade_informada is not None and unidade_informada != usuario.unidadeId:
            raise AcessoNegadoError("Voce nao tem acesso a esta unidade.")
        return usuario.unidadeId
    if unidade_informada is None:
        if obrigatorio:
            raise ValidacaoError("Informe a unidade.")
        return None
    return unidade_informada


def garantir_escopo(usuario, unidade_id):
    if usuario.unidadeId is not None and unidade_id != usuario.unidadeId:
        raise AcessoNegadoError("Voce nao tem acesso a este recurso.")

