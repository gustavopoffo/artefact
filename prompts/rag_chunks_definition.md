# Definição dos Chunks RAG — Empório da Música
## Documento: políticas_da_loja.pdf

Este documento define os chunks para busca semântica. Cada chunk é uma unidade autônoma de informação.

---

## Seção 3: Formas de Pagamento

### Chunk 3.0 — Formas de Pagamento (Visão Geral)
**Categoria:** `pagamento`
**Keywords:** `["pagamento", "pix", "cartão", "débito", "crédito", "boleto", "desconto", "à vista"]`

```
A Empório da Música aceita as seguintes formas de pagamento para compras presenciais e online:

- PIX: Pagamento à vista com 5% de desconto sobre o preço de tabela.
- Cartão de Débito: Pagamento à vista. Todas as bandeiras aceitas.
- Cartão de Crédito: Parcelamento em até 12x sem juros. Parcela mínima de R$ 100,00.
- Boleto Bancário: Pagamento à vista. Compensação em até 3 dias úteis.
```

### Chunk 3.1 — Regras de Parcelamento
**Categoria:** `pagamento`
**Keywords:** `["parcelamento", "parcela", "juros", "crédito", "valor mínimo", "combinar pagamento"]`

```
Regras de Parcelamento no Cartão de Crédito:

- Parcelamento em até 3x: sem juros, sem valor mínimo de parcela (exceto abaixo de R$ 50,00).
- Parcelamento de 4x a 6x: sem juros, parcela mínima de R$ 80,00.
- Parcelamento de 7x a 12x: sem juros, parcela mínima de R$ 100,00.
- Combinação de formas de pagamento: permitida (ex.: PIX + cartão) para compras acima de R$ 2.000,00.
```

---

## Seção 4: Política de Trocas e Devoluções

### Chunk 4.0 — Direito de Arrependimento (Compras Online)
**Categoria:** `troca`
**Keywords:** `["arrependimento", "devolução", "7 dias", "online", "reembolso", "frete devolução"]`

```
Direito de Arrependimento para Compras Online:

- O cliente pode solicitar a devolução em até 7 (sete) dias corridos após o recebimento do produto, sem necessidade de justificativa.
- O produto deve estar em sua embalagem original, sem sinais de uso, com todos os acessórios e manuais.
- O reembolso será realizado na mesma forma de pagamento original em até 10 dias úteis.
- O frete de devolução é por conta da loja em caso de arrependimento.

Conforme o Código de Defesa do Consumidor (Lei nº 8.078/90).
```

### Chunk 4.1 — Trocas por Defeito
**Categoria:** `troca`
**Keywords:** `["defeito", "fabricação", "30 dias", "garantia", "troca defeito", "mau uso"]`

```
Trocas por Defeito de Fabricação:

- Produtos com defeito de fabricação podem ser trocados em até 30 (trinta) dias corridos após a compra.
- Após os 30 dias, o cliente deve acionar a garantia diretamente com o fabricante. A Empório da Música pode intermediar o processo mediante solicitação.

NÃO SÃO COBERTOS:
- Danos causados por mau uso
- Danos por quedas
- Exposição a umidade excessiva
- Modificações não autorizadas
```

### Chunk 4.2 — Trocas por Preferência
**Categoria:** `troca`
**Keywords:** `["troca preferência", "cor", "modelo", "tamanho", "7 dias", "diferença valor"]`

```
Trocas por Preferência (cor, modelo, tamanho):

- Permitidas em até 7 dias após a compra.
- Sujeitas à disponibilidade do produto desejado.
- O produto deve estar em perfeito estado e na embalagem original.
- Diferenças de valor serão cobradas ou reembolsadas conforme o caso.
```

### Chunk 4.3 — Itens Não Elegíveis para Troca
**Categoria:** `troca`
**Keywords:** `["não troca", "personalização", "liquidação", "venda final", "boquilha", "sopro", "higiene"]`

```
Itens que NÃO podem ser trocados:

- Instrumentos com personalização ou ajustes sob encomenda (setup, regulagem especial).
- Produtos adquiridos em promoções de liquidação com aviso explícito de "venda final".
- Boquilhas de instrumentos de sopro, por questões de higiene.
```

---

## Seção 5: Política de Frete e Entregas

### Chunk 5.0 — Entregas na Região Metropolitana de Campo Grande
**Categoria:** `frete`
**Keywords:** `["frete grátis", "Campo Grande", "motoboy", "entrega local", "R$ 500", "R$ 35"]`

```
Entregas na Região Metropolitana de Campo Grande:

- Frete grátis para pedidos acima de R$ 500,00.
- Para pedidos abaixo de R$ 500,00, taxa fixa de R$ 35,00.
- Prazo de entrega: 1 a 3 dias úteis.
- Entrega realizada por motoboy próprio. O cliente será contactado por telefone antes da entrega.
```

### Chunk 5.1 — Entregas para Outras Cidades
**Categoria:** `frete`
**Keywords:** `["Correios", "PAC", "SEDEX", "Jadlog", "transportadora", "prazo", "rastreamento", "seguro"]`

```
Entregas para Outras Cidades (fora da região metropolitana de Campo Grande):

Utilizamos Correios (PAC e SEDEX) e transportadora Jadlog.

| Modalidade | Prazo Estimado | Rastreamento | Seguro |
|------------|----------------|--------------|--------|
| PAC (Correios) | 5 a 12 dias úteis | Sim | Incluído |
| SEDEX (Correios) | 2 a 5 dias úteis | Sim | Incluído |
| Jadlog (.package) | 3 a 8 dias úteis | Sim | Incluído |

- O valor do frete é calculado com base no CEP de destino, peso e dimensões.
- Instrumentos de grande porte (baterias, pianos digitais, contrabaixos) podem exigir frete especial com cotação individual.
- Todos os envios incluem seguro contra extravios e danos.
- Em caso de avaria, o cliente deve recusar o recebimento e entrar em contato imediatamente.
```

### Chunk 5.2 — Código de Rastreamento
**Categoria:** `frete`
**Keywords:** `["rastreamento", "código", "rastrear", "pedido", "enviado", "despachado"]`

```
Código de Rastreamento:

- Enviado automaticamente por e-mail e WhatsApp assim que o pedido é despachado.
- Formato padrão: BR seguido de 9 caracteres alfanuméricos e BR (exemplo: BR4K7M2X9P1BR).
- Pode ser consultado diretamente no site dos Correios ou da Jadlog.
```

---

## Seção 6: Promoções e Descontos

### Chunk 6.0 — Tipos de Promoção
**Categoria:** `promocao`
**Keywords:** `["promoção", "desconto", "Black Friday", "aniversário", "volta às aulas", "queima estoque"]`

```
Principais Campanhas Promocionais da Empório da Música:

- Aniversário da Loja (Agosto): descontos de 10% a 25% em itens selecionados.
- Black Friday (Novembro): descontos de 15% a 30% em todo o catálogo.
- Volta às Aulas (Fevereiro): descontos especiais em instrumentos para estudantes.
- Queima de Estoque: promoções pontuais para renovação de catálogo.
- Semana do Músico: promoções na semana do Dia do Músico (22 de novembro).
```

### Chunk 6.1 — Regras de Promoções
**Categoria:** `promocao`
**Keywords:** `["cumulativo", "desconto PIX", "estoque", "rain check", "preço promocional"]`

```
Regras de Promoções:

CUMULATIVIDADE: Promoções NÃO são cumulativas. O desconto de PIX (5%) não se aplica sobre preços já promocionais.

ESTOQUE: Promoções estão sujeitas à disponibilidade de estoque. Produtos esgotados durante a promoção não geram direito a rain check (reserva de preço).

COMUNICAÇÃO: Preços promocionais devem sempre ser apresentados junto ao preço original e o percentual de desconto, para total transparência.
```

---

## Seção 8: Garantia

### Chunk 8.0 — Garantia Legal e do Fabricante
**Categoria:** `garantia`
**Keywords:** `["garantia", "90 dias", "fabricante", "defeito", "6 meses", "2 anos", "CDC"]`

```
Garantia dos Produtos:

GARANTIA LEGAL (CDC):
- Todos os produtos possuem garantia legal de 90 (noventa) dias contra defeitos de fabricação.
- Contados a partir da data de recebimento pelo cliente.

GARANTIA DO FABRICANTE:
- Além da garantia legal, a maioria dos fabricantes oferece garantia própria de 6 meses a 2 anos.
- Prazos e condições específicos estão no certificado de garantia que acompanha cada produto.
```

### Chunk 8.1 — O que Não Cobre a Garantia
**Categoria:** `garantia`
**Keywords:** `["não cobre", "desgaste", "mau uso", "queda", "modificação", "terceiros"]`

```
O que NÃO é coberto pela garantia:

- Desgaste natural de peças (trastes, cordas, feltros, palhetas de sopro).
- Danos por mau uso, queda, exposição a condições climáticas extremas.
- Modificações ou reparos realizados por terceiros não autorizados.
- Danos estéticos que não afetem a funcionalidade do instrumento.
```

---

## Seção 9: Privacidade e Proteção de Dados (LGPD)

### Chunk 9.0 — LGPD e Uso de Dados
**Categoria:** `lgpd`
**Keywords:** `["LGPD", "dados pessoais", "privacidade", "exclusão", "consentimento", "Lei 13.709"]`

```
Privacidade e Proteção de Dados (LGPD):

A Empório da Música está em conformidade com a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018).

Os dados pessoais coletados (nome, telefone, e-mail, endereço) são utilizados exclusivamente para:
- Processamento e entrega de pedidos.
- Comunicação sobre status de pedidos e rastreamento.
- Envio de promoções e novidades (mediante consentimento explícito).
- Cumprimento de obrigações legais e fiscais.

DIREITOS DO CLIENTE:
- Dados NÃO são compartilhados com terceiros para fins de marketing.
- O cliente pode solicitar a exclusão de seus dados a qualquer momento via WhatsApp ou e-mail.
```

---

## Resumo dos Chunks

| Seção | Chunks | Categoria |
|-------|--------|-----------|
| 3. Formas de Pagamento | 2 | `pagamento` |
| 4. Trocas e Devoluções | 4 | `troca` |
| 5. Frete e Entregas | 3 | `frete` |
| 6. Promoções | 2 | `promocao` |
| 8. Garantia | 2 | `garantia` |
| 9. LGPD | 1 | `lgpd` |
| **TOTAL** | **14 chunks** | |

---

## Critérios de Design dos Chunks

1. **Autossuficiência:** Cada chunk contém informação completa e compreensível isoladamente.
2. **Granularidade:** Chunks pequenos o suficiente para precisão, grandes o suficiente para contexto.
3. **Categorização:** Permite filtro por categoria na busca (ex: só buscar em `pagamento`).
4. **Keywords:** Termos de busca auxiliar para casos onde embedding não é suficiente.
5. **Numeração:** Preserva relação com documento original (ex: 4.1 = Seção 4, Chunk 1).
