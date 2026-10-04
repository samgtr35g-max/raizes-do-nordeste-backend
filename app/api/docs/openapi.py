"""Documentacao OpenAPI/Swagger da API (Flasgger).

Este modulo contem apenas a especificacao, refletindo exatamente os
endpoints e o comportamento ja implementados. Nao altera regras de negocio.
"""
from flasgger import Swagger

ERRO = {"$ref": "#/definitions/ErrorResponse"}


def _respostas(extras=None):
    base = {
        "401": {"description": "Nao autenticado (token ausente/invalido/expirado)", "schema": ERRO},
        "403": {"description": "Acesso negado (sem permissao ou fora do escopo de unidade)", "schema": ERRO},
    }
    if extras:
        base.update(extras)
    return base


def openapi_template():
    return {
        "swagger": "2.0",
        "info": {
            "title": "Rede Raizes do Nordeste - API",
            "description": (
                "API REST do projeto multidisciplinar Rede Raizes do Nordeste. "
                "Endpoints protegidos usam autenticacao JWT no cabecalho "
                "`Authorization: Bearer <token>`."
            ),
            "version": "1.0.0",
        },
        "basePath": "/",
        "schemes": ["http"],
        "consumes": ["application/json"],
        "produces": ["application/json"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "Informe o token no formato: Bearer <token>",
            }
        },
        "tags": [
            {"name": "Auth", "description": "Autenticacao e dados do usuario autenticado"},
            {"name": "Estoque", "description": "Consulta e movimentacoes de estoque por unidade"},
            {"name": "Pedidos", "description": "Criacao, consulta, status e cancelamento de pedidos"},
            {"name": "Pagamentos", "description": "Pagamentos via gateway simulado (mock)"},
            {"name": "Fidelidade", "description": "Programa de fidelidade (pontos)"},
            {"name": "Clientes", "description": "Privacidade e LGPD (anonimizacao de dados pessoais)"},
        ],
        "paths": {
            "/auth/login": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Autentica um usuario",
                    "description": "Valida email e senha e retorna um token JWT. Nao revela se o email existe.",
                    "consumes": ["application/json"],
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "required": True,
                            "schema": {"$ref": "#/definitions/LoginRequest"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Login efetuado",
                            "schema": {"$ref": "#/definitions/LoginResponse"},
                        },
                        "400": {"description": "Email ou senha ausentes", "schema": ERRO},
                        "401": {"description": "Credenciais invalidas", "schema": ERRO},
                        "403": {"description": "Usuario inativo", "schema": ERRO},
                        "422": {"description": "Dados invalidos", "schema": ERRO},
                    },
                }
            },
            "/auth/me": {
                "get": {
                    "tags": ["Auth"],
                    "summary": "Dados do usuario autenticado",
                    "description": "Retorna apenas dados nao sensiveis do usuario do token. Nunca retorna senhaHash.",
                    "security": [{"Bearer": []}],
                    "responses": _respostas(
                        {"200": {"description": "Usuario autenticado", "schema": {"$ref": "#/definitions/UsuarioResponse"}}}
                    ),
                }
            },
            "/estoque": {
                "get": {
                    "tags": ["Estoque"],
                    "summary": "Consulta estoque",
                    "description": "Consulta estoque por unidade e/ou produto. Usuario interno ve apenas a propria unidade.",
                    "security": [{"Bearer": []}],
                    "parameters": [
                        {"name": "unidadeId", "in": "query", "type": "integer", "required": False},
                        {"name": "produtoId", "in": "query", "type": "integer", "required": False},
                    ],
                    "responses": _respostas(
                        {"200": {"description": "Lista de estoques", "schema": {"type": "array", "items": {"$ref": "#/definitions/EstoqueResponse"}}}}
                    ),
                }
            },
            "/estoque/entrada": {
                "post": {
                    "tags": ["Estoque"],
                    "summary": "Registra entrada de estoque",
                    "description": "Requer permissao ESTOQUE_AJUSTAR. Cria o registro de estoque quando nao existe.",
                    "security": [{"Bearer": []}],
                    "parameters": [{"name": "body", "in": "body", "required": True, "schema": {"$ref": "#/definitions/MovimentacaoEstoqueRequest"}}],
                    "responses": _respostas(
                        {
                            "201": {"description": "Entrada registrada", "schema": {"$ref": "#/definitions/MovimentacaoEstoqueResponse"}},
                            "404": {"description": "Unidade ou produto nao encontrado", "schema": ERRO},
                            "422": {"description": "Quantidade invalida", "schema": ERRO},
                        }
                    ),
                }
            },
            "/estoque/saida": {
                "post": {
                    "tags": ["Estoque"],
                    "summary": "Registra saida de estoque",
                    "description": "Requer permissao ESTOQUE_AJUSTAR. Nao permite saida maior que o disponivel.",
                    "security": [{"Bearer": []}],
                    "parameters": [{"name": "body", "in": "body", "required": True, "schema": {"$ref": "#/definitions/MovimentacaoEstoqueRequest"}}],
                    "responses": _respostas(
                        {
                            "201": {"description": "Saida registrada", "schema": {"$ref": "#/definitions/MovimentacaoEstoqueResponse"}},
                            "404": {"description": "Unidade, produto ou estoque nao encontrado", "schema": ERRO},
                            "409": {"description": "Estoque insuficiente", "schema": ERRO},
                            "422": {"description": "Quantidade invalida", "schema": ERRO},
                        }
                    ),
                }
            },
            "/estoque/ajuste": {
                "post": {
                    "tags": ["Estoque"],
                    "summary": "Ajusta a quantidade do estoque",
                    "description": "Requer permissao ESTOQUE_AJUSTAR. O cliente envia a quantidade-alvo; o servidor calcula a diferenca e registra a movimentacao.",
                    "security": [{"Bearer": []}],
                    "parameters": [{"name": "body", "in": "body", "required": True, "schema": {"$ref": "#/definitions/MovimentacaoEstoqueRequest"}}],
                    "responses": _respostas(
                        {
                            "201": {"description": "Ajuste registrado", "schema": {"$ref": "#/definitions/MovimentacaoEstoqueResponse"}},
                            "404": {"description": "Unidade ou produto nao encontrado", "schema": ERRO},
                            "422": {"description": "Quantidade invalida ou ajuste sem alteracao", "schema": ERRO},
                        }
                    ),
                }
            },
            "/pedidos": {
                "post": {
                    "tags": ["Pedidos"],
                    "summary": "Cria um pedido",
                    "description": (
                        "Cria pedido com itens, valida estoque e aplica a melhor promocao "
                        "(sem acumulo). Os valores (valorProdutos, valorDesconto, valorTotal, "
                        "valorUnitario) sao SEMPRE calculados pelo servidor; valores enviados "
                        "pelo cliente sao ignorados. Estoque insuficiente retorna 409."
                    ),
                    "security": [{"Bearer": []}],
                    "parameters": [{"name": "body", "in": "body", "required": True, "schema": {"$ref": "#/definitions/PedidoRequest"}}],
                    "responses": _respostas(
                        {
                            "201": {"description": "Pedido criado", "schema": {"$ref": "#/definitions/PedidoResponse"}},
                            "404": {"description": "Unidade, produto ou cliente nao encontrado", "schema": ERRO},
                            "409": {"description": "Estoque insuficiente", "schema": ERRO},
                            "422": {"description": "Dados invalidos (canal, quantidade, produto inativo)", "schema": ERRO},
                        }
                    ),
                },
                "get": {
                    "tags": ["Pedidos"],
                    "summary": "Lista pedidos",
                    "description": "Filtra por canalPedido, status e unidadeId. Usuario interno ve apenas a propria unidade.",
                    "security": [{"Bearer": []}],
                    "parameters": [
                        {"name": "canalPedido", "in": "query", "type": "string", "enum": ["APP", "TOTEM", "BALCAO", "PICKUP", "WEB"], "required": False},
                        {"name": "status", "in": "query", "type": "string", "enum": ["RECEBIDO", "EM_PREPARO", "PRONTO", "CONCLUIDO", "CANCELADO"], "required": False},
                        {"name": "unidadeId", "in": "query", "type": "integer", "required": False},
                    ],
                    "responses": _respostas(
                        {"200": {"description": "Lista de pedidos", "schema": {"type": "array", "items": {"$ref": "#/definitions/PedidoResponse"}}}}
                    ),
                },
            },
            "/pedidos/{id}": {
                "get": {
                    "tags": ["Pedidos"],
                    "summary": "Consulta um pedido",
                    "description": "Retorna o pedido com itens e historico de status.",
                    "security": [{"Bearer": []}],
                    "parameters": [{"name": "id", "in": "path", "type": "integer", "required": True}],
                    "responses": _respostas(
                        {
                            "200": {"description": "Pedido", "schema": {"$ref": "#/definitions/PedidoResponse"}},
                            "404": {"description": "Pedido nao encontrado", "schema": ERRO},
                        }
                    ),
                }
            },
            "/pedidos/{id}/status": {
                "patch": {
                    "tags": ["Pedidos"],
                    "summary": "Altera o status do pedido",
                    "description": (
                        "Requer permissao PEDIDO_CANCELAR. Transicoes validas: "
                        "RECEBIDO -> EM_PREPARO -> PRONTO -> CONCLUIDO. Cancelamento deve "
                        "usar o endpoint proprio. Transicao invalida retorna 409."
                    ),
                    "security": [{"Bearer": []}],
                    "parameters": [
                        {"name": "id", "in": "path", "type": "integer", "required": True},
                        {"name": "body", "in": "body", "required": True, "schema": {"$ref": "#/definitions/StatusPedidoRequest"}},
                    ],
                    "responses": _respostas(
                        {
                            "200": {"description": "Status alterado", "schema": {"$ref": "#/definitions/PedidoResponse"}},
                            "404": {"description": "Pedido nao encontrado", "schema": ERRO},
                            "409": {"description": "Transicao de status invalida", "schema": ERRO},
                            "422": {"description": "Status invalido", "schema": ERRO},
                        }
                    ),
                }
            },
            "/pedidos/{id}/cancelamento": {
                "post": {
                    "tags": ["Pedidos"],
                    "summary": "Cancela o pedido",
                    "description": "Requer permissao PEDIDO_CANCELAR. Devolve o estoque e estorna pontos acumulados quando aplicavel. Nao cancela pedidos CONCLUIDO/CANCELADO.",
                    "security": [{"Bearer": []}],
                    "parameters": [
                        {"name": "id", "in": "path", "type": "integer", "required": True},
                        {"name": "body", "in": "body", "required": False, "schema": {"$ref": "#/definitions/CancelamentoRequest"}},
                    ],
                    "responses": _respostas(
                        {
                            "200": {"description": "Pedido cancelado", "schema": {"$ref": "#/definitions/PedidoResponse"}},
                            "404": {"description": "Pedido nao encontrado", "schema": ERRO},
                            "409": {"description": "Pedido nao pode ser cancelado no status atual", "schema": ERRO},
                        }
                    ),
                }
            },
            "/pedidos/{id}/pagamentos": {
                "get": {
                    "tags": ["Pedidos"],
                    "summary": "Lista pagamentos do pedido",
                    "security": [{"Bearer": []}],
                    "parameters": [{"name": "id", "in": "path", "type": "integer", "required": True}],
                    "responses": _respostas(
                        {
                            "200": {"description": "Lista de pagamentos", "schema": {"type": "array", "items": {"$ref": "#/definitions/PagamentoResponse"}}},
                            "404": {"description": "Pedido nao encontrado", "schema": ERRO},
                        }
                    ),
                }
            },
            "/pagamentos": {
                "post": {
                    "tags": ["Pagamentos"],
                    "summary": "Solicita um pagamento (gateway simulado)",
                    "description": (
                        "O valor e obtido do pedido no servidor (nunca do cliente). Nao se usa "
                        "dados reais de cartao. Pagamento aprovado NAO altera o status operacional "
                        "do pedido; concede pontos de fidelidade (1 ponto por R$ 1,00 inteiro). "
                        "Pedido com pagamento aprovado retorna 409."
                    ),
                    "security": [{"Bearer": []}],
                    "parameters": [{"name": "body", "in": "body", "required": True, "schema": {"$ref": "#/definitions/PagamentoRequest"}}],
                    "responses": _respostas(
                        {
                            "201": {"description": "Pagamento registrado (APROVADO ou RECUSADO)", "schema": {"$ref": "#/definitions/PagamentoResponse"}},
                            "404": {"description": "Pedido nao encontrado", "schema": ERRO},
                            "409": {"description": "Pedido nao pagavel ou pagamento duplicado", "schema": ERRO},
                            "422": {"description": "Metodo invalido", "schema": ERRO},
                        }
                    ),
                }
            },
            "/pagamentos/{id}": {
                "get": {
                    "tags": ["Pagamentos"],
                    "summary": "Consulta um pagamento",
                    "security": [{"Bearer": []}],
                    "parameters": [{"name": "id", "in": "path", "type": "integer", "required": True}],
                    "responses": _respostas(
                        {
                            "200": {"description": "Pagamento", "schema": {"$ref": "#/definitions/PagamentoResponse"}},
                            "404": {"description": "Pagamento nao encontrado", "schema": ERRO},
                        }
                    ),
                }
            },
            "/clientes/{id}/fidelidade": {
                "get": {
                    "tags": ["Fidelidade"],
                    "summary": "Consulta a conta de fidelidade",
                    "description": "Retorna o cliente, o saldo e o historico de movimentacoes. O proprio cliente acessa apenas seus dados; usuarios internos acessam conforme o programa.",
                    "security": [{"Bearer": []}],
                    "parameters": [{"name": "id", "in": "path", "type": "integer", "required": True}],
                    "responses": _respostas(
                        {
                            "200": {"description": "Conta de fidelidade", "schema": {"$ref": "#/definitions/FidelidadeResponse"}},
                            "404": {"description": "Cliente nao encontrado", "schema": ERRO},
                        }
                    ),
                }
            },
            "/clientes/{id}/fidelidade/resgate": {
                "post": {
                    "tags": ["Fidelidade"],
                    "summary": "Resgata pontos de fidelidade",
                    "description": "Debita pontos da conta. Saldo insuficiente retorna 409. Saldo nunca fica negativo.",
                    "security": [{"Bearer": []}],
                    "parameters": [
                        {"name": "id", "in": "path", "type": "integer", "required": True},
                        {"name": "body", "in": "body", "required": True, "schema": {"$ref": "#/definitions/ResgateRequest"}},
                    ],
                    "responses": _respostas(
                        {
                            "201": {"description": "Resgate efetuado", "schema": {"$ref": "#/definitions/FidelidadeResponse"}},
                            "404": {"description": "Cliente nao encontrado", "schema": ERRO},
                            "409": {"description": "Saldo insuficiente", "schema": ERRO},
                            "422": {"description": "Quantidade de pontos invalida", "schema": ERRO},
                        }
                    ),
                }
            },
            "/clientes/{id}/anonimizacao": {
                "post": {
                    "tags": ["Clientes"],
                    "summary": "Anonimiza os dados pessoais do cliente (LGPD)",
                    "description": (
                        "Remove/mascara dados pessoais (nome -> ANONIMIZADO, CPF/email/"
                        "telefone/dataNascimento -> null) e marca anonimizado=true, "
                        "preservando registros necessarios. O proprio cliente ou usuarios "
                        "internos autorizados podem executar. A acao e auditada."
                    ),
                    "security": [{"Bearer": []}],
                    "parameters": [{"name": "id", "in": "path", "type": "integer", "required": True}],
                    "responses": _respostas(
                        {
                            "200": {"description": "Cliente anonimizado", "schema": {"$ref": "#/definitions/ClienteAnonimizadoResponse"}},
                            "404": {"description": "Cliente nao encontrado", "schema": ERRO},
                        }
                    ),
                }
            },
        },
        "definitions": {
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "erro": {
                        "type": "object",
                        "properties": {
                            "codigo": {"type": "string", "example": "credenciais_invalidas"},
                            "mensagem": {"type": "string", "example": "Email ou senha invalidos."},
                        },
                    }
                },
            },
            "ClienteAnonimizadoResponse": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "nome": {"type": "string", "example": "ANONIMIZADO"},
                    "anonimizado": {"type": "boolean", "example": True},
                },
            },
            "LoginRequest": {
                "type": "object",
                "required": ["email", "senha"],
                "properties": {
                    "email": {"type": "string", "example": "admin@raizes.dev"},
                    "senha": {"type": "string", "example": "Admin@123"},
                },
            },
            "LoginResponse": {
                "type": "object",
                "properties": {
                    "access_token": {"type": "string", "example": "eyJhbGciOiJIUzI1NiJ9.exemplo.token"},
                    "token_type": {"type": "string", "example": "Bearer"},
                    "expires_in": {"type": "integer", "example": 28800},
                },
            },
            "UsuarioResponse": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "nome": {"type": "string", "example": "Administrador DEV"},
                    "email": {"type": "string", "example": "admin@raizes.dev"},
                    "ativo": {"type": "boolean", "example": True},
                    "unidadeId": {"type": "integer", "x-nullable": True, "example": None},
                    "criadoEm": {"type": "string", "example": "2026-10-04T12:00:00"},
                },
            },
            "EstoqueResponse": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "unidadeId": {"type": "integer", "example": 1},
                    "produtoId": {"type": "integer", "example": 1},
                    "quantidadeAtual": {"type": "integer", "example": 50},
                    "quantidadeMinima": {"type": "integer", "example": 10},
                },
            },
            "MovimentacaoEstoqueRequest": {
                "type": "object",
                "required": ["unidadeId", "produtoId", "quantidade"],
                "properties": {
                    "unidadeId": {"type": "integer", "example": 1},
                    "produtoId": {"type": "integer", "example": 1},
                    "quantidade": {"type": "integer", "example": 10, "description": "Para ajuste, representa a quantidade-alvo."},
                    "motivo": {"type": "string", "example": "Reposicao de estoque"},
                },
            },
            "MovimentacaoEstoqueResponse": {
                "type": "object",
                "properties": {
                    "estoque": {"$ref": "#/definitions/EstoqueResponse"},
                    "movimentacao": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "example": 1},
                            "tipo": {"type": "string", "enum": ["ENTRADA", "SAIDA", "AJUSTE"], "example": "ENTRADA"},
                            "quantidade": {"type": "integer", "example": 10},
                            "motivo": {"type": "string", "x-nullable": True, "example": "Reposicao de estoque"},
                            "pedidoId": {"type": "integer", "x-nullable": True, "example": None},
                            "usuarioId": {"type": "integer", "x-nullable": True, "example": 1},
                            "criadoEm": {"type": "string", "example": "2026-10-04T12:00:00"},
                        },
                    },
                },
            },
            "ItemPedidoRequest": {
                "type": "object",
                "required": ["produtoId", "quantidade"],
                "properties": {
                    "produtoId": {"type": "integer", "example": 1},
                    "quantidade": {"type": "integer", "example": 2},
                    "observacao": {"type": "string", "example": "Sem cebola"},
                },
            },
            "PedidoRequest": {
                "type": "object",
                "required": ["unidadeId", "canalPedido", "itens"],
                "properties": {
                    "unidadeId": {"type": "integer", "example": 1},
                    "clienteId": {"type": "integer", "x-nullable": True, "example": 1},
                    "canalPedido": {"type": "string", "enum": ["APP", "TOTEM", "BALCAO", "PICKUP", "WEB"], "example": "APP"},
                    "itens": {"type": "array", "items": {"$ref": "#/definitions/ItemPedidoRequest"}},
                    "observacao": {"type": "string", "example": "Sem cebola"},
                },
            },
            "PedidoResponse": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "unidadeId": {"type": "integer", "example": 1},
                    "clienteId": {"type": "integer", "x-nullable": True, "example": 1},
                    "usuarioId": {"type": "integer", "x-nullable": True, "example": 1},
                    "canalPedido": {"type": "string", "enum": ["APP", "TOTEM", "BALCAO", "PICKUP", "WEB"], "example": "APP"},
                    "status": {"type": "string", "enum": ["RECEBIDO", "EM_PREPARO", "PRONTO", "CONCLUIDO", "CANCELADO"], "example": "RECEBIDO"},
                    "valorProdutos": {"type": "string", "example": "24.00"},
                    "valorDesconto": {"type": "string", "example": "2.40"},
                    "valorTotal": {"type": "string", "example": "21.60"},
                    "observacao": {"type": "string", "x-nullable": True, "example": "Sem cebola"},
                    "criadoEm": {"type": "string", "example": "2026-10-04T12:00:00"},
                },
            },
            "StatusPedidoRequest": {
                "type": "object",
                "required": ["status"],
                "properties": {
                    "status": {"type": "string", "enum": ["EM_PREPARO", "PRONTO", "CONCLUIDO"], "example": "EM_PREPARO"},
                    "observacao": {"type": "string", "example": "Pedido iniciado pela cozinha"},
                },
            },
            "CancelamentoRequest": {
                "type": "object",
                "properties": {"observacao": {"type": "string", "example": "Cliente desistiu"}},
            },
            "PagamentoRequest": {
                "type": "object",
                "required": ["pedidoId", "metodo"],
                "properties": {
                    "pedidoId": {"type": "integer", "example": 1},
                    "metodo": {"type": "string", "enum": ["PIX", "CARTAO", "DINHEIRO"], "example": "PIX"},
                    "simularResultado": {
                        "type": "string",
                        "enum": ["APROVADO", "RECUSADO"],
                        "description": "RECURSO DE DESENVOLVIMENTO do mock. Forca o resultado para testes. Nao usar em producao.",
                        "example": "APROVADO",
                    },
                },
            },
            "PagamentoResponse": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "pedidoId": {"type": "integer", "example": 1},
                    "valor": {"type": "string", "example": "21.60"},
                    "metodo": {"type": "string", "enum": ["PIX", "CARTAO", "DINHEIRO"], "example": "PIX"},
                    "status": {"type": "string", "enum": ["PENDENTE", "APROVADO", "RECUSADO", "ESTORNADO"], "example": "APROVADO"},
                    "provedor": {"type": "string", "example": "MockGateway"},
                    "idTransacaoExterna": {"type": "string", "example": "MOCK-PIX-1-1700000000000-1"},
                    "payloadResposta": {"type": "string", "example": "{\"status\": \"APROVADO\", \"provedor\": \"MockGateway\"}"},
                    "criadoEm": {"type": "string", "example": "2026-10-04T12:00:00"},
                    "atualizadoEm": {"type": "string", "example": "2026-10-04T12:00:00"},
                },
            },
            "ResgateRequest": {
                "type": "object",
                "required": ["pontos"],
                "properties": {"pontos": {"type": "integer", "example": 20}},
            },
            "FidelidadeResponse": {
                "type": "object",
                "properties": {
                    "cliente": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "example": 1},
                            "nome": {"type": "string", "example": "Cliente Teste DEV"},
                        },
                    },
                    "saldoPontos": {"type": "integer", "example": 80},
                    "movimentacoes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer", "example": 1},
                                "tipo": {"type": "string", "enum": ["ACUMULO", "RESGATE", "ESTORNO", "EXPIRACAO"], "example": "ACUMULO"},
                                "pontos": {"type": "integer", "example": 35},
                                "pedidoId": {"type": "integer", "x-nullable": True, "example": 1},
                                "criadoEm": {"type": "string", "example": "2026-10-04T12:00:00"},
                            },
                        },
                    },
                },
            },
        },
    }


def configurar_documentacao(app):
    """Inicializa o Flasgger com a especificacao do projeto."""
    app.config["SWAGGER"] = {
        "title": "Rede Raizes do Nordeste - API",
        "uiversion": 3,
        "specs_route": "/docs/",
    }
    Swagger(app, template=openapi_template())
