# Frontend — Empório da Música

Interface React (Vite + Tailwind) do agente:

| Rota | Função |
|------|--------|
| `/` | Chat do cliente |
| `/admin` | Conversas + rating |
| `/admin/dashboard` | Métricas |
| `/admin/promocoes` | Ativar/desativar promoções |
| `/admin/modelo` | Modelo OpenAI (`gpt-4o` padrão) |

## Desenvolvimento

```bash
cp .env.example .env   # VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

Documentação completa do projeto (API, banco, deploy): ver [README na raiz](../README.md).

Demo: https://emporio-five.vercel.app/
