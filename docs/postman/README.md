# Collection Postman - Raizes do Nordeste

Collection de testes manuais da API (complementar ao Swagger em `/docs/`).

Arquivos:
- `raizes-do-nordeste.postman_collection.json`
- `raizes-do-nordeste.postman_environment.json`

## 1. Iniciar a API

```powershell
Copy-Item .env.example .env      # ajuste JWT_SECRET_KEY (>= 32 bytes)
.\venv\Scripts\Activate.ps1
flask --app run db upgrade
python -m app.infrastructure.database.seeds.seed
flask --app run run
```

A API sobe em `http://127.0.0.1:5000` (e o Swagger em `/docs/`).

## 2. Importar a Collection

No Postman: **Import** -> selecione o arquivo `raizes-do-nordeste.postman_collection.json`.
Opcionalmente importe tambem o `raizes-do-nordeste.postman_environment.json` e selecione o
ambiente **"Raizes do Nordeste - DEV"**.

## 3. Configurar `baseUrl`

A Collection ja define `baseUrl = http://127.0.0.1:5000`. Se necessario, altere na aba
**Variables** da Collection (ou no Environment).

## 4. Executar o Login

Rode **01 - Auth > Login** (usa as credenciais de desenvolvimento do seed:
`admin@raizes.dev` / `Admin@123`). O script de teste salva automaticamente o `token`
(nao imprimimos o token em console). Depois, **04 - Auth > Me** preenche `usuarioId`.

## 5. Executar os demais requests

A Collection usa autenticacao **Bearer** no nivel da Collection (`Authorization: Bearer {{token}}`),
entao os endpoints protegidos ja herdam o token. Rode a pasta **02 - Estoque** primeiro:
o request "Consultar estoque" preenche `unidadeId` e `produtoId` automaticamente.

Ordem sugerida (ou use o Collection Runner):
1. 01 - Auth
2. 02 - Estoque
3. 03 - Pedidos
4. 04 - Pagamentos
5. 05 - Fidelidade
6. 06 - LGPD
7. 07 - Casos de erro

## 6. Variaveis preenchidas automaticamente

| Variavel | Onde e preenchida |
|---|---|
| `token` | Login (a partir de `access_token`) |
| `usuarioId` | Me |
| `unidadeId` / `produtoId` | Consultar estoque |
| `pedidoId` | Criar pedido |
| `pagamentoId` | Criar pagamento aprovado |
| `pedidoCancelarId` | Criar pedido auxiliar (para cancelamento) |
| `pedidoRecusadoId` | Criar pedido auxiliar (para pagamento recusado) |
| `clienteId` | Valor padrao do seed (`1`); ajuste se necessario |

## 7. Requests destrutivos / de teste

- **`[DESTRUTIVO] Cancelar pedido`** - cancela o pedido auxiliar (devolve estoque).
- **`[ATENCAO - IRREVERSIVEL] Anonimizar cliente`** - remove os dados pessoais do
  cliente `{{clienteId}}`. Nao ha como desfazer. Use apenas cliente de teste/seed.
- **`[DEV] Criar pagamento recusado (simularResultado)`** - usa o recurso de
  desenvolvimento do mock (`simularResultado=RECUSADO`); nao usar em producao.
- **`07 - Casos de erro`** - nao altera o estado do sistema; apenas valida respostas
  de erro (401/404/409/422).

## Observacoes

- Nenhum dado sensivel real e usado: credenciais sao de desenvolvimento, sem CPF/email
  pessoal, sem cartao, sem JWT/segredo fixos.
- Os valores monetarios do pedido **nao** sao enviados pelo cliente; o servidor calcula.
