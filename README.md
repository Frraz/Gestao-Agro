# 🌾 Sistema de Gestão Agrícola

![Interface do Sistema](docs/img/telaprincipal.png)  
[![Deploy Railway](https://img.shields.io/badge/Railway-Deploy-brightgreen?logo=railway)](https://gestao-agro-production.up.railway.app/)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Issues](https://img.shields.io/github/issues/Frraz/Gestao-Agro-Beta)](https://github.com/Frraz/Gestao-Agro-Beta/issues)
[![Stars](https://img.shields.io/github/stars/Frraz/Gestao-Agro-Beta?style=social)](https://github.com/Frraz/Gestao-Agro-Beta/stargazers)
<!-- [![Build Status](https://github.com/Frraz/Gestao-Agro-Beta/actions/workflows/ci.yml/badge.svg)](https://github.com/Frraz/Gestao-Agro-Beta/actions) -->

> **Gestão rural moderna, produtiva e automatizada. Foco em produtividade, controle financeiro e documentação.**  
> **Para produtores rurais, consultorias e empresas do agronegócio.**

---

## 📑 Sumário

- [🔎 Veja online e Documentação](#-veja-online-e-documentação)
- [✨ Por que usar o Gestao-Agro?](#-por-que-usar-o-gestao-agro)
- [📋 Principais Funcionalidades](#-principais-funcionalidades)
- [🛠️ Tecnologias e Arquitetura](#️-tecnologias-e-arquitetura)
- [🚀 Instalação Rápida](#-instalação-rápida)
- [☁️ Deploy no Railway](#️-deploy-no-railway)
- [🧪 Testes](#-testes)
- [🐳 Docker](#-docker)
- [🔧 Manutenção e Tarefas Automáticas](#-manutenção-e-tarefas-automáticas)
- [📋 Requisitos](#-requisitos)
- [📁 Estrutura do Projeto](#-estrutura-do-projeto)
- [✨ Melhorias da Versão 2.0](#-principais-melhorias-da-versão-20)
- [📊 Métricas de Melhoria](#-métricas-de-melhoria)
- [🔮 Roadmap Futuro](#-roadmap-futuro)
- [🤝 Como Contribuir](#-como-contribuir)
- [📄 Licença](#-licença)
- [📞 Suporte](#-suporte)
- [❓ FAQ](#-faq)

---

## 🔎 Veja online e Documentação

- [➡️ **Acesse a demonstração**](https://gestao-agro-production.up.railway.app/)
- [📚 **Documentação completa**](docs/README.md)

---

## ✨ Por que usar o Gestao-Agro?

- **Automatize notificações de vencimentos** (até 7 alertas por e-mail)
- Controle total de pessoas, fazendas, documentos e endividamentos
- **Dashboard visual, responsivo e moderno**
- Segurança, performance e facilidade de uso
- Código aberto e fácil de customizar

---

## 📋 Principais Funcionalidades

| Pessoa/Fazenda                         | Documentos                       | Endividamentos                   | Notificações         | Visual            |
|:--------------------------------------- |:---------------------------------|:---------------------------------|:---------------------|:------------------|
| Cadastro completo com CPF/CNPJ          | Upload, tipos e controle         | Valor, garantias, parcelas       | 7 alertas automáticos| Tema escuro/claro |
| Associação a múltiplas fazendas/áreas   | Datas de emissão e vencimento    | Relatórios financeiros           | Histórico de envios  | Mobile-first      |
| Controle de vínculos e relacionamentos  | Notificação automática           | Detalhamento de crédito/garantias| Config. flexível     | Animações suaves  |

---

## 🛠️ Tecnologias e Arquitetura

**Backend:**  
- Flask, SQLAlchemy, MySQL/SQLite, Redis, Celery

**Frontend:**  
- Bootstrap 5, JavaScript ES6+, Font Awesome, CSS Custom Properties

**Performance:**  
- Cache inteligente com Redis, consultas otimizadas, índices estratégicos, compressão de recursos, lazy loading, rate limiting

---

## 🚀 Instalação Rápida

```bash
git clone https://github.com/Frraz/Gestao-Agro-Beta.git
cd Gestao-Agro-Beta
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env      # Edite o arquivo com suas configurações
python src/main.py
```

---

## ☁️ Deploy no Railway

1. Clique em [Deploy on Railway](https://railway.app/new)
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

## 🐳 Docker

```bash
docker-compose up --build
```

---

## 🔧 Manutenção e Tarefas Automáticas

```bash
python maintenance.py --task notificacoes
python maintenance.py --task cache
python maintenance.py --task banco
python maintenance.py --task scheduler
```

**Tarefas automáticas:**  
- Notificações: a cada hora
- Limpeza de cache: a cada 2 horas
- Otimização de banco: diariamente às 2:00
- Backup de logs: semanalmente aos domingos às 3:00

---

## 📋 Requisitos

- Python 3.8+
- MySQL 5.7+ ou SQLite (para desenvolvimento)
- Redis (opcional, para cache)
- Servidor SMTP para envio de e-mails

---

## 📁 Estrutura do Projeto

```
Gestao-Agro-Beta/
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

**Curto Prazo (1-3 meses)**
- API REST para integração externa
- Dashboard com gráficos avançados
- Exportação de relatórios em PDF/Excel
- Sistema de backup automatizado

**Médio Prazo (3-6 meses)**
- Aplicativo móvel nativo
- Integração bancária
- Análise preditiva de vencimentos
- Sistema de workflow para aprovações

**Longo Prazo (6-12 meses)**
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

Veja as [issues abertas](https://github.com/Frraz/Gestao-Agro-Beta/issues) e contribua!

---

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 📞 Suporte

- Abra uma [issue](https://github.com/Frraz/Gestao-Agro-Beta/issues)
- [Documentação completa](docs/)
- [Relatório de melhorias](RELATORIO_MELHORIAS_COMPLETO.md)

---

## ❓ FAQ

**1. O sistema funciona em Windows/Linux/Mac?**  
Sim, é multiplataforma. Basta ter Python 3.8+ instalado.

**2. Preciso de MySQL obrigatoriamente?**  
Não. Para testes e ambiente de desenvolvimento, SQLite já funciona. MySQL é recomendado para produção.

**3. O sistema é gratuito?**  
Sim, 100% open source sob licença MIT.

---

**Desenvolvido com ❤️ para a gestão agrícola moderna**

*Sistema de Gestão Agrícola - Transformando a gestão rural com tecnologia*
