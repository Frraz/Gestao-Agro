# Sistema de Gestão Agrícola

![Interface do Sistema](docs/img/Tela%20principal.png) 
[![Deploy Railway](https://img.shields.io/badge/Railway-Deploy-brightgreen?logo=railway)](https://gestao-agro-production.up.railway.app/)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
<!-- Adicione aqui badge de status do GitHub Actions se usar CI -->

> Gestão rural inteligente, moderna e automatizada, focada em produtividade, controle financeiro e documentação.

## 🔥 Veja online:
➡️ [Acesse a demonstração](https://gestao-agro-production.up.railway.app/)

---

## ✨ Por que usar o Gestao-Agro?

- **Automatize notificações de vencimentos** (até 7 alertas por e-mail)
- Controle total de pessoas, fazendas, documentos e endividamentos
- **Dashboard visual, responsivo e moderno**
- Segurança, performance e facilidade de uso
- Código aberto e fácil de customizar

---

## 📋 Funcionalidades Principais

| Pessoa/Fazenda                         | Documentos                       | Endividamentos                   | Notificações         | Visual            |
|:--------------------------------------- |:---------------------------------|:---------------------------------|:---------------------|:------------------|
| Cadastro completo com CPF/CNPJ          | Upload, tipos e controle         | Valor, garantias, parcelas       | 7 alertas automáticos| Tema escuro/claro |
| Associação a múltiplas fazendas/áreas   | Datas de emissão e vencimento    | Relatórios financeiros           | Histórico de envios  | Mobile-first      |
| Controle de vínculos e relacionamentos  | Notificação automática           | Detalhamento de crédito/garantias| Config. flexível     | Animações suaves  |

---

## 🚀 Principais Funcionalidades

### 👥 Gestão de Pessoas
- Cadastro completo com CPF/CNPJ
- Associação a múltiplas fazendas/áreas
- Controle de relacionamentos e vínculos

### 🏞️ Gestão de Fazendas/Áreas
- Matrícula do imóvel, tamanho total, área consolidada e disponível
- Tipo de posse (Própria, Arrendada, Comodato, Posse)
- Estado e município com seleção dinâmica
- Número do recibo do CAR (opcional)

### 📄 Gestão de Documentação
- Certidões, Contratos, Documentos da Área, Outros
- Controle de datas de emissão e vencimento
- Sistema de notificações por e-mail com múltiplos prazos
- Configuração de múltiplos e-mails para notificação
- Alertas automáticos de vencimento

### 💰 Gerenciamento de Endividamentos
- Empréstimos e financiamentos detalhados
- Valor da operação, garantias, parcelas, carência e juros
- Vinculação a múltiplas pessoas e fazendas
- Notificações automáticas (6m, 3m, 30d, 15d, 7d, 3d, 1d)
- Histórico de notificações enviadas

### 🎨 Interface Moderna
- Design responsivo (desktop, tablet e mobile)
- Tema escuro/claro com alternância automática
- Navegação otimizada e animações suaves

### 📊 Dashboard e Relatórios
- Estatísticas, alertas de vencimentos, indicadores visuais e métricas de performance

---

## 🛠️ Tecnologias e Arquitetura

**Backend:**  
- Flask, SQLAlchemy, MySQL/SQLite, Redis, Celery

**Frontend:**  
- Bootstrap 5, JavaScript ES6+, Font Awesome, CSS Custom Properties

**Performance:**  
- Cache inteligente com Redis, consultas otimizadas, índices estratégicos, compressão de recursos, lazy loading, rate limiting

---

## 📋 Requisitos

- Python 3.8+
- MySQL 5.7+ ou SQLite (para desenvolvimento)
- Redis (opcional, para cache)
- Servidor SMTP para envio de e-mails

---

## 🚀 Instalação Rápida

```bash
git clone https://github.com/Frraz/Gestao-Agro.git
cd Gestao-Agro
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env      # Edite o arquivo com suas configurações
python src/main.py
```

Acesse [documentação completa em `/docs`](docs/README.md)

---

## ☁️ Deploy no Railway

1. Clique em [Deploy on Railway](https://railway.app/new) <!-- Ou badge/link automático -->
2. Configure as variáveis de ambiente
3. Pronto! O sistema subirá automaticamente

---

## 🧪 Testes

```bash
chmod +x run_tests.sh
./run_tests.sh
```

### Testar com MySQL

```bash
chmod +x test_mysql.sh
./test_mysql.sh
```

---

## 🔧 Manutenção e Tarefas Automáticas

```bash
# Notificações manuais
python maintenance.py --task notificacoes

# Limpar cache
python maintenance.py --task cache

# Otimizar banco de dados
python maintenance.py --task banco

# Executar scheduler automático
python maintenance.py --task scheduler
```

**Tarefas automáticas:**  
- Notificações: a cada hora
- Limpeza de cache: a cada 2 horas
- Otimização de banco: diariamente às 2:00
- Backup de logs: semanalmente aos domingos às 3:00

---

## 🐳 Deploy Local com Docker

```bash
docker-compose up --build
```

---

## 📁 Estrutura do Projeto

```
Gestao-Agro/
├── src/
│   ├── models/
│   ├── routes/
│   ├── forms/
│   ├── static/
│   ├── templates/
│   ├── utils/
│   └── main.py
├── tests/
├── docs/
├── logs/
├── uploads/
├── maintenance.py
├── requirements.txt
└── README.md
```

---

## ✨ Principais Melhorias da Versão 2.0

- Sistema de notificações automáticas por e-mail com múltiplos intervalos
- Novo campo de valor da operação para endividamentos
- Interface moderna, responsiva e com tema escuro/claro
- Sistema de cache distribuído (Redis) e otimizações de performance
- Segurança aprimorada (rate limiting, validação, logging)

---

## 📊 Métricas de Melhoria

- ⚡ **40% redução** no tempo de resposta médio
- 🗃️ **60% menos consultas** ao banco de dados
- 📱 **100% responsivo** em todos os dispositivos
- 🔔 **7 intervalos** de notificação automática
- 🎨 **2 temas** (claro e escuro) com alternância automática

---

## 🔮 Roadmap Futuro

### Curto Prazo (1-3 meses)
- API REST para integração externa
- Dashboard com gráficos avançados
- Exportação de relatórios em PDF/Excel
- Sistema de backup automatizado

### Médio Prazo (3-6 meses)
- Aplicativo móvel nativo
- Integração bancária
- Análise preditiva de vencimentos
- Sistema de workflow para aprovações

### Longo Prazo (6-12 meses)
- Inteligência artificial para análise de riscos
- Integração com IoT para monitoramento
- Sistema de geolocalização
- Marketplace para serviços agrícolas

---

## 🤝 Como Contribuir

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/NomeDaFeature`)
3. Commit suas mudanças (`git commit -m 'feat: Minha melhoria'`)
4. Push para a branch (`git push origin feature/NomeDaFeature`)
5. Abra um Pull Request

Veja as [issues abertas](https://github.com/Frraz/Gestao-Agro/issues) e contribua!

---

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 📞 Suporte

- Abra uma [issue](https://github.com/Frraz/Gestao-Agro/issues)
- [Documentação completa](docs/)
- [Relatório de melhorias](RELATORIO_MELHORIAS_COMPLETO.md)

---

**Desenvolvido com ❤️ para a gestão agrícola moderna**

*Sistema de Gestão Agrícola v1.0 - Transformando a gestão rural com tecnologia*