# 📄 Guia de Atualização do Sistema (Beta → Alfa)

Este documento descreve o processo seguro e completo para atualizar a **versão de produção (alfa)** com as melhorias da **versão de desenvolvimento (beta)**, garantindo que os dados do banco de dados não sejam perdidos.

---

## ✅ Etapas da Atualização

### 1. 🔐 Backup do Banco de Dados (Obrigatório)

Antes de qualquer ação:

```bash
mysqldump -u <usuario> -p <nome_do_banco> > backup_producao.sql
```

Armazene esse arquivo em local seguro.

---

### 2. 🔀 Mesclando a Versão Beta na Alfa

Se os repositórios são separados:

```bash
# Navegue até o diretório da versão alfa
cd Gestao-Agro-Alfa

git checkout main

git remote add beta https://github.com/Frraz/Gestao-Agro-Beta.git
git fetch beta
git merge beta/main --allow-unrelated-histories
```

> Resolva conflitos manualmente, principalmente em arquivos como `.env`, `requirements.txt`, `main.py`, `config.py`, etc.

---

### 3. 📦 Atualização de Dependências

```bash
pip install -r requirements.txt
```

Verifique se houve adição de novas bibliotecas no `requirements.txt` da versão beta.

---

### 4. 🧬 Migração de Banco de Dados

Se estiver usando `Flask-Migrate`:

```bash
flask db migrate -m "Atualização da beta"
flask db upgrade
```

Se **não** estiver usando, faça ajustes no modelo e execute comandos SQL manualmente para aplicar mudanças no banco.

> Recomenda-se fortemente o uso de `Flask-Migrate` para versões futuras.

---

### 5. 🧪 Teste em Ambiente de Staging

Antes de atualizar a produção, faça testes com os dados reais em um ambiente separado:

* Clone o banco
* Rode o sistema com as mudanças
* Verifique funcionalidades, notificações, uploads e logs

---

### 6. 🚀 Deploy para Produção

Após os testes:

1. Faça push da branch mesclada no repositório de produção
2. Railway fará o deploy automático
3. Monitore logs em tempo real

---

### 7. ⚙️ Atualize `.env` da Produção

Adicione novas variáveis utilizadas na versão beta:

* `MAIL_SERVER`, `REDIS_URL`, `CACHE_TIMEOUT`, etc.

Sempre confira o arquivo `.env.example` da beta.

---

### 8. 📁 Pastas Persistentes

Garanta que essas pastas não sejam sobrescritas:

```
/uploads
/logs
```

Essas devem estar no `.gitignore` e configuradas como pastas persistentes na Railway (ou onde for).

---

### 9. 🔍 Pós-deploy: Checklist Rápido

* [ ] Login funcionando
* [ ] CRUDs testados
* [ ] Envio de e-mails
* [ ] Notificações agendadas
* [ ] Dados antigos preservados
* [ ] Logs sem erros graves

---

## 🛠️ Recomendações Futuras

* Adotar `Flask-Migrate` para facilitar evolução do schema
* Automatizar o processo com um script de upgrade
* Manter arquivo `CHANGELOG.md` com histórico de versões

---

**Esse guia deve ser consultado sempre que uma atualização for feita da versão Beta para Alfa.**

*Desenvolvido com ❤️ para manter seu sistema sempre atualizado e seguro.*
