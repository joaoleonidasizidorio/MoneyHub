# MoneyHub 💸

**MoneyHub** é um sistema financeiro pessoal premium, desenvolvido para ser leve, seguro e esteticamente agradável. Construído com **Flask (Python)** e empacotado em **Docker**, ele permite o controle total sobre suas receitas e despesas com um design moderno em *Dark Mode* e *Glassmorphism*.

Um de seus diferenciais é a integração com a Inteligência Artificial (Google Gemini), permitindo a leitura automática de cupons fiscais através de imagens.

---

## 🌟 Principais Funcionalidades

### 1. 📊 Dashboard Inteligente
*   Visão global do seu dinheiro com separação clara de Receitas e Despesas **Mensais**.
*   Balanço total da conta (Global).
*   Visualização rápida das últimas 5 transações efetuadas.

### 2. 🧾 OCR com Inteligência Artificial (Leitor de Cupom)
*   **Integração com Google Gemini Vision**: Faça upload da foto do seu cupom fiscal, e a IA extrai automaticamente:
    *   **Valor da compra** (ex: R$ 150,00)
    *   **Descrição/Nome do Estabelecimento** (ex: Supermercado XYZ)
    *   **Data da compra**
*   Segurança de Dados: A foto é processada em memória e imediatamente deletada para economizar armazenamento e proteger a privacidade do usuário.

### 3. 👤 Gestão de Perfil e Segurança
*   **Avatar Personalizado**: Faça upload da sua foto de perfil. Ela é exibida em todo o painel de navegação (Sidebar).
*   **Troca de E-mail**: Atualize seu e-mail de contato de forma segura.
*   **Troca de Senha Blindada**: Requer validação da senha atual. Todas as senhas são hasheadas usando `Bcrypt` antes de irem para o banco de dados.

### 4. 🎨 Design Premium
*   O sistema não utiliza frameworks CSS inflados (como Bootstrap). Todo o design foi construído em **CSS Puro (Vanilla CSS)**.
*   **Dark Mode Nativo**: Cores otimizadas para leitura à noite.
*   **Glassmorphism**: Painéis translúcidos (efeito de vidro fosco) utilizando `backdrop-filter: blur`, entregando a sensação de um SaaS moderno e de alto valor.
*   **Responsivo**: Funciona perfeitamente tanto no computador quanto na tela do seu celular.

---

## 🛠️ Tecnologias Utilizadas

*   **Backend:** Python 3.10, Flask
*   **Banco de Dados:** SQLite (leve e local, ideal para uso pessoal)
*   **Frontend:** HTML5, CSS3, ícones `Bootstrap Icons`
*   **Autenticação e Segurança:** Flask-Login (gestão de sessão) e Flask-Bcrypt (hashing de senhas).
*   **Inteligência Artificial:** `google-generativeai` (Gemini 1.5 Flash).
*   **Infraestrutura:** Docker e Docker Compose.

---

## 🚀 Como Rodar o Projeto (Localmente)

Para rodar este projeto na sua máquina, você só precisa do **Docker** e do **Docker Compose** instalados.

### 1. Clonar o repositório
```bash
git clone https://github.com/joaoleonidasizidorio/MoneyHub.git
cd moneyhub
```

### 2. Configurar Variáveis de Ambiente
Crie um arquivo chamado `.env` na raiz do projeto (use o `.env.example` como base) e insira sua chave da API do Google Gemini:
```env
GEMINI_API_KEY=sua_chave_aqui
```

### 3. Subir os Containers com Docker
O projeto já está 100% conteinerizado. Basta rodar:
```bash
docker compose up -d --build
```

### 4. Acessar o Sistema
Abra o seu navegador e acesse:
👉 **[http://localhost:5005](http://localhost:5005)**

*(Ao acessar pela primeira vez, clique em "Crie agora" na tela de login para registrar o seu usuário administrador)*

---

## 🔒 Segurança dos Dados
Todo o seu histórico financeiro é armazenado localmente em um banco de dados SQLite (`instance/finance.db`). Como o diretório raiz é montado como um **Volume** no Docker (`.:/app`), o seu banco de dados, variáveis de ambiente e fotos de perfil nunca serão perdidos caso você reinicie ou apague o container. 

Além disso, regras no arquivo `.gitignore` previnem que estes arquivos sejam acidentalmente enviados ao GitHub.
