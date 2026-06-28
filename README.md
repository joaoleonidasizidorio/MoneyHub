# MoneyHub - Gestor Financeiro com Inteligência Artificial 💰🤖

MoneyHub é uma aplicação web de gestão financeira pessoal construída com arquitetura moderna, design focado em Experiência do Usuário (Glassmorphism) e recursos avançados de Inteligência Artificial usando a API do Google Gemini.

## 🛠 Tecnologias Utilizadas

### Backend (Servidor)
* **Linguagem:** Python 3.10+
* **Framework Web:** Flask
* **ORM e Banco de Dados:** Flask-SQLAlchemy com banco relacional **SQLite** (`moneyhub.db`)
* **Autenticação:** Flask-Login (gerenciamento de sessão segura)
* **Geração de PDF:** ReportLab (para exportação de relatórios oficias)
* **Integração IA:** Google Generative AI REST API (Modelo: `gemini-flash-lite-latest`)

### Frontend (Interface)
* **Estrutura:** HTML5 + Jinja2 Templates (Motor de templates do Flask)
* **Estilização:** CSS3 Vanilla puro (Design System exclusivo focado em Glassmorphism, sem dependência de Tailwind ou Bootstrap)
* **Lógica de Cliente:** Javascript (Vanilla) + Fetch API para requisições assíncronas.
* **Gráficos:** Chart.js (Visualização de dados dinâmicos)
* **Ícones:** Bootstrap Icons (via CDN)

### Infraestrutura
* **Containerização:** Docker e Docker Compose (Garante que o ambiente rode perfeitamente em qualquer máquina).

---

## 🗄 Estrutura do Banco de Dados

O banco de dados relacional (SQLite) possui 3 tabelas principais altamente integradas:

1. **`User` (Usuários)**
   - `id`, `username`, `password` (Hashed).
   - Relacionamentos de "Um para Muitos" com Transações e Orçamentos.

2. **`Transaction` (Transações)**
   - `id`, `amount`, `type` (`income` = Receita, `expense` = Despesa), `category`, `description`, `date`, `is_paid`, `user_id`.
   - Armazena o fluxo de caixa histórico.

3. **`Budget` (Orçamentos)**
   - `id`, `category`, `amount`, `user_id`.
   - Define limites mensais que o usuário estabelece para categorias específicas (ex: Lazer = R$ 500/mês).

---

## 🚀 Funcionalidades Principais (Core)

* **Autenticação e Segurança:** Sistema de Login e Registro com senhas criptografadas. Proteção de rotas garantindo que usuários só vejam seus próprios dados.
* **Dashboard Analítico:** Painel de controle que calcula saldo atual, total de receitas, despesas e exibe um gráfico "Donut" interativo das despesas por categoria.
* **Gestão de Lançamentos:** Tela para adicionar transações manualmente, categorizar e marcar como pagas/pendentes.
* **Gestão de Orçamentos:** Tela dedicada para o usuário definir tetos de gastos. A barra de progresso do Dashboard muda de verde para vermelho se o teto for rompido.
* **Relatório Oficial em PDF:** Geração dinâmica de extrato financeiro mensal em formato PDF estilizado, pronto para impressão ou contabilidade.

---

## 🧠 Funcionalidades de Inteligência Artificial (Módulo IA)

O grande diferencial do MoneyHub são as integrações assíncronas com o modelo `Gemini Flash Lite` do Google, atuando como um assistente invisível e proativo.

### 1. Leitor de Cupom Mágico (OCR com Visão Computacional)
* **Como funciona:** O usuário não precisa digitar os gastos do mercado. Basta selecionar a imagem de uma nota fiscal ou cupom. O Frontend converte a imagem para Base64 e envia para a IA através da rota `/api/scan_receipt`.
* **Processamento:** A IA lê a imagem, extrai o valor total gasto e categoriza a compra automaticamente. Ela devolve um JSON padronizado que preenche o formulário de cadastro num passe de mágica.

### 2. Chatbot Consultor Financeiro (Floating UI)
* **Como funciona:** Um botão flutuante no canto da tela abre uma janela de bate-papo.
* **Processamento (`/api/chat`):** Quando o usuário faz uma pergunta, o backend empacota o histórico recente de transações (últimas 20) e os limites de orçamento. Esse contexto é injetado no cérebro da IA, que assume a "persona" de um consultor rigoroso. Ele responde a perguntas como *"Posso comprar um tênis hoje?"* baseando-se no saldo real do usuário no banco de dados.

### 3. Previsão de Gastos (Forecasting Analítico)
* **Como funciona:** Um card de vidro proeminente no Dashboard.
* **Processamento (`/api/forecast`):** Ao carregar a tela, uma requisição silenciosa envia para a IA o dia atual do mês e o volume de gastos. A IA cruza a velocidade do gasto com o limite do orçamento. Se o ritmo estiver muito alto, ela devolve um alerta antecipado (ex: *"No ritmo atual, você vai estourar Lazer no dia 22"*).

### 4. Cão de Guarda: Detecção de Anomalias
* **Como funciona:** Um Banner Vermelho de alerta (invisível por padrão) no topo do painel.
* **Processamento (`/api/anomalies`):** A cada visita no Dashboard, o sistema busca os últimos 4 meses de despesas (como Luz, Internet, etc) agrupados. A IA analisa as médias históricas. Se encontrar um aumento abusivo no mês atual (ex: um pico de 50% na conta de energia), ela dispara o gatilho, fazendo o Banner Vermelho aparecer para o usuário investigar a fatura.

---

## 💻 Como Rodar o Projeto

1. **Requisitos:** Docker e Docker Compose instalados.
2. **Chave de API:** Tenha sua chave de API do Gemini no arquivo `.env` (variável `GEMINI_API_KEY`).
3. **Subindo o servidor:**
   Execute no terminal:
   ```bash
   docker compose up --build -d
   ```
4. **Acesso:**
   Abra o navegador e acesse: `http://localhost:5001`
