# 🚀 DDL Converter Web Application

Aplicação web moderna para conversão de arquivos DDL (Data Definition Language) do mainframe DB2 para configurações JSON compatíveis com pipelines MLOps, com interface estilo FreeConverter.com.

**Desenvolvido por Felipe Machado - Serasa Experian**
**Data: 15/09/2025**

---

## ✨ Características Principais

- 🌐 **Interface Web Moderna**
- 📁 **Upload Múltiplo**: Envie vários arquivos DDL simultaneamente
- 🔄 **Processamento em Lote**: Processa todos os arquivos de uma vez
- 🛡️ **Prevenção de Duplicatas**: Evita reprocessamento de arquivos já convertidos
- 📦 **Cache Inteligente**: Gerenciamento automático de arquivos temporários
- 💾 **Download Flexível**: Baixe arquivos individuais ou todos em ZIP
- 🧹 **Limpeza Automática**: Cache limpo automaticamente ao reiniciar

---

## 🚀 Como Usar

### 📋 Pré-requisitos

- **Python 3.8+** instalado no sistema
- **Conexão com internet** para instalar dependências

### 1️⃣ Iniciar a Aplicação

```bash
# 1. Navegue até a pasta do projeto
cd ddl-converter-web

# 2. Instalar dependências (apenas na primeira vez)
pip install -r requirements.txt

# 3. Iniciar o servidor web
python app.py
```

**Você verá esta mensagem:**

```
=== DDL Converter Web Application ===
Iniciando servidor web...
Abrindo navegador automaticamente...
Acesse: http://localhost:5000
=====================================
```

**O navegador abrirá automaticamente** em `http://localhost:5000` após 1.5 segundos!

### 2️⃣ Usar a Interface Web

#### ✅ **Passo 1: Enviar Arquivos**
- Arraste seus arquivos `.txt` ou `.ddl` para a área azul
- OU clique em "Selecionar Arquivos"

#### ✅ **Passo 2: Processar**
- Clique no botão **"Processar Arquivos"**
- Aguarde a barra de progresso completar

#### ✅ **Passo 3: Baixar Resultados**
- **CSV individual**: Clique no botão "CSV" 
- **JSON individual**: Clique no botão "JSON"
- **Todos juntos**: Clique em "Baixar Todos (ZIP)"

### 3️⃣ Compartilhar na Rede (Opcional)

**Para outras pessoas usarem na mesma rede Wi-Fi:**

1. **Descubra seu IP:**
   - Windows: `ipconfig` no cmd
   - Mac/Linux: `ifconfig` no terminal

2. **Compartilhe o endereço:**
   - `http://SEU_IP:5000`
   - Exemplo: `http://192.168.1.100:5000`

### 🛑 Para Parar

- Pressione `Ctrl + C` no terminal
- Feche o terminal

### 3️⃣ Acessar a Interface

**O navegador abre automaticamente!** Mas se precisar abrir manualmente:

1. **Abra seu navegador** (Chrome, Firefox, Edge, Safari)
2. **Digite na barra de endereços**: `http://localhost:5000`
3. **Pressione Enter** - a interface será carregada

### 4️⃣ Converter Arquivos DDL

#### 📤 **Enviar Arquivos**

- **Arraste e solte** seus arquivos DDL na área azul
- **OU clique em "Selecionar Arquivos"** para escolher do computador
- **Formatos aceitos**: `.txt`, `.ddl`
- **Tamanho máximo**: 16MB por arquivo

#### ⚙️ **Processar**

1. Após enviar, clique em **"Processar Arquivos"**
2. **Aguarde** - uma barra de progresso aparecerá
3. **Acompanhe** o status em tempo real

#### 💾 **Baixar Resultados**

- **Arquivos individuais**: Clique nos botões "CSV" ou "JSON"
- **Todos os arquivos**: Clique em "Baixar Todos (ZIP)"
- **Arquivos salvos em**: `cache/output/`

#### 🛑 **Parar a Aplicação**

- **Pressione `Ctrl + C`** no terminal onde está rodando
- **Feche o terminal** para parar completamente

---

## 📁 Estrutura do Projeto

```
ddl-converter-web/
├── app.py                    # Aplicação Flask principal
├── conversor_ddl.py          # Lógica de conversão DDL
├── requirements.txt          # Dependências Python
├── README.md                # Este arquivo
├── templates/
│   └── index.html           # Interface HTML principal
├── static/
│   ├── css/
│   │   └── style.css        # Estilos CSS (FreeConverter style)
│   └── js/
│       └── script.js        # JavaScript interativo
├── sample_ddls/             # Arquivos DDL de exemplo
│   └── RS_DIVIDA_VENCIDA.txt
└── cache/                   # Diretório temporário (auto-gerenciado)
    ├── uploads/             # Arquivos enviados
    └── output/              # Arquivos processados
        ├── dicionarios/     # CSVs gerados
        └── json/            # JSONs MLOps
```

---

## 🔧 Funcionalidades Técnicas

### ✅ Conversão Automática

- **Extração de estruturas** de tabelas e colunas
- **Conversão de tipos** do mainframe para MLOps
- **Geração de metadados** automaticamente
- **Campos de auditoria** incluídos automaticamente

### 🛡️ Controle de Duplicatas

- **Hash de arquivos** para identificação única
- **Verificação automática** de arquivos já processados
- **Notificação** de arquivos ignorados

### 📦 Gerenciamento de Cache

- **Limpeza automática** ao iniciar a aplicação
- **Diretórios temporários** criados automaticamente
- **Remoção segura** de arquivos antigos

### 🔄 Processamento Assíncrono

- **Threads em background** para processamento
- **Monitoramento em tempo real** do progresso
- **Interface responsiva** durante o processamento

---

## 🎨 Interface do Usuário

### 📱 Design Responsivo

- **Mobile-friendly** para todos os dispositivos
- **Drag & Drop** intuitivo para upload
- **Animações suaves** e feedback visual
- **Notificações** em tempo real

### 🎯 Experiência do Usuário

- **Progresso visual** durante processamento
- **Resultados organizados** por arquivo
- **Downloads individuais** ou em lote
- **Mensagens de erro** claras e úteis

---

## 📊 Tipos de Conversão Suportados

| Tipo Mainframe | Tipo MLOps       | Exemplo                    |
| -------------- | ---------------- | -------------------------- |
| `VARCHAR(n)` | `string`       | VARCHAR(50) → string      |
| `CHAR(n)`    | `string`       | CHAR(10) → string         |
| `INTEGER`    | `integer`      | INTEGER → integer         |
| `SMALLINT`   | `integer`      | SMALLINT → integer        |
| `DEC(p,s)`   | `decimal(p,s)` | DEC(10,2) → decimal(10,2) |
| `DATE`       | `date`         | DATE → date               |
| `TIMESTAMP`  | `timestamp`    | TIMESTAMP → timestamp     |
| `TIME`       | `string`       | TIME → string             |

---

## 🚨 Recursos de Segurança

- **Validação de arquivos** por extensão
- **Tamanho máximo** de 16MB por arquivo
- **Sanitização** de nomes de arquivos
- **Isolamento** de diretórios temporários

---

## 📋 Arquivos Gerados

### 📄 CSV (Dicionário)

- **Localização**: `cache/output/dicionarios/NOME_TABELA.csv`
- **Conteúdo**: Metadados da tabela e colunas
- **Formato**: Separado por ponto-e-vírgula (;)

### 📦 JSON (MLOps)

- **Localização**: `cache/output/json/nome_tabela.json`
- **Conteúdo**: Configuração completa para pipelines
- **Formato**: JSON estruturado com metadados completos

---

## 🔍 API Endpoints

| Endpoint             | Método | Descrição              |
| -------------------- | ------- | ------------------------ |
| `/`                | GET     | Interface principal      |
| `/upload`          | POST    | Upload de arquivos       |
| `/process`         | POST    | Iniciar processamento    |
| `/status/<id>`     | GET     | Verificar progresso      |
| `/download/<path>` | GET     | Download de arquivo      |
| `/download_all`    | GET     | Download ZIP completo    |
| `/clear_cache`     | POST    | Limpar cache manualmente |

---

## 🐛 Solução de Problemas

| Problema                    | Solução                                                |
| --------------------------- | -------------------------------------------------------- |
| Erro ao iniciar aplicação | Verificar se Flask está instalado:`pip install flask` |
| Arquivos não aparecem      | Verificar extensões permitidas (.txt, .ddl)             |
| Processamento falha         | Verificar formato do DDL (deve conter CREATE TABLE)      |
| Cache muito grande          | Usar endpoint `/clear_cache` ou reiniciar aplicação  |
| Erro de permissão          | Executar com permissões adequadas de escrita            |

---

## 🔧 Configurações Avançadas

### Personalizar Porta

```python
# No final do app.py, altere:
app.run(debug=True, host='0.0.0.0', port=8080)  # Porta 8080
```

### Aumentar Tamanho Máximo

```python
# No app.py, altere:
MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB
```

### Adicionar Extensões

```python
# No app.py, altere:
ALLOWED_EXTENSIONS = {'txt', 'ddl', 'sql'}  # Adicionar .sql
```

---

## 📞 Suporte

**Desenvolvedor**: Felipe Machado
**Email**: felipe.machado2@experian.com
**Empresa**: Serasa Experian

Para problemas técnicos, melhorias ou dúvidas sobre o conversor.

---

## 📝 Changelog

### v2.0.0 - Web Application

- ✅ Interface web completa
- ✅ Upload múltiplo de arquivos
- ✅ Processamento em lote
- ✅ Prevenção de duplicatas
- ✅ Cache inteligente
- ✅ Downloads em ZIP

### v1.0.0 - CLI Original

- ✅ Processamento via linha de comando
- ✅ Conversão DDL para JSON
- ✅ Geração de CSV dicionário

---

## 🎯 Próximas Funcionalidades

- [ ] Histórico de processamentos
- [ ] Configurações personalizáveis
- [ ] Suporte a mais formatos de entrada
- [ ] API REST completa
- [ ] Autenticação de usuários
- [ ] Logs detalhados

---

**🚀 Pronto para converter seus arquivos DDL com facilidade!**
