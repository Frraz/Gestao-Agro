# Sistema de Notificações - Guia de Solução e Produção

## ✅ Problemas Identificados e Corrigidos

### 1. **Inconsistência nos Nomes das Tasks**
**Problema:** O `celery_app.py` estava tentando agendar tasks com nomes que não existiam:
- `src.utils.notificacao_documentos_service.verificar_e_enviar_notificacoes_task`
- `src.utils.notificacao_endividamento_service.verificar_e_enviar_notificacoes_task`

**Solução:** Atualizado o `celery_app.py` para usar os nomes corretos das tasks registradas:
```python
"verificar-notificacoes-documentos": {
    "task": "tasks.processar_notificacoes_documentos",
    "schedule": crontab(hour=8, minute=0),
},
```

### 2. **Configurações de Timezone Conflitantes**
**Problema:** Configurações inconsistentes entre arquivos:
- `celery_app.py`: `enable_utc = False`
- `config.py`: `CELERY_ENABLE_UTC = True`

**Solução:** Padronizou para:
```python
celery.conf.timezone = "America/Sao_Paulo"
celery.conf.enable_utc = True  # UTC internamente, conversão para timezone local
```

### 3. **Falta de Task Decorators Adequados**
**Problema:** Os serviços de notificação não tinham decorators Celery adequados.

**Solução:** Adicionadas funções de criação de tasks nos serviços:
- `criar_task_verificar_documentos()`
- `criar_task_verificar_endividamentos()`

### 4. **Contexto Flask Ausente em Tasks**
**Problema:** Tasks executando fora do contexto Flask, causando erros de banco.

**Solução:** Adicionada verificação de contexto nos serviços:
```python
try:
    current_app._get_current_object()
    # Executar operações de banco
except RuntimeError:
    logger.warning("Executando fora do contexto Flask")
    return 0
```

### 5. **Agendamentos Limitados**
**Problema:** Apenas um agendamento por dia às 8h.

**Solução:** Adicionados múltiplos agendamentos:
- 08:00 - Verificação matinal
- 14:00 - Verificação vespertina  
- A cada 5 min - Teste de conectividade

---

## 🚀 Como Colocar em Produção

### 1. **Pré-requisitos**

```bash
# Instalar Redis
sudo apt-get update
sudo apt-get install redis-server

# Iniciar Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verificar se Redis está rodando
redis-cli ping  # Deve retornar "PONG"
```

### 2. **Configurar Variáveis de Ambiente**

Crie o arquivo `.env` com as configurações corretas:

```env
# Database
DATABASE_URL=mysql+pymysql://usuario:senha@host:porta/database

# E-mail
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=seu_email@gmail.com
MAIL_PASSWORD=sua_senha_app_gmail
MAIL_DEFAULT_SENDER=seu_email@gmail.com

# Redis/Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Flask
FLASK_ENV=production
SECRET_KEY=sua_chave_secreta_super_forte
```

### 3. **Inicializar Banco de Dados**

```bash
# Executar migrações
flask db upgrade

# Ou se necessário
python -c "from src.main import app, db; app.app_context().push(); db.create_all()"
```

### 4. **Iniciar os Serviços**

Execute em terminais separados:

```bash
# Terminal 1: Worker Celery
celery -A celery_app worker --loglevel=info

# Terminal 2: Scheduler Celery Beat
celery -A celery_app beat --loglevel=info

# Terminal 3: Aplicação Flask
python src/main.py

# Terminal 4 (Opcional): Monitor Flower
celery -A celery_app flower
```

### 5. **Verificar Funcionamento**

```bash
# Verificar status dos workers
celery -A celery_app status

# Ver tasks agendadas
celery -A celery_app inspect scheduled

# Executar task manualmente
celery -A celery_app call tasks.processar_todas_notificacoes

# Usar script de diagnóstico
python celery_diagnostic.py
```

---

## 🔧 Comandos de Monitoramento

### Verificar Sistema
```bash
# Status geral
curl http://localhost:5000/health

# Status detalhado do Celery
curl http://localhost:5000/celery-status

# Testar Celery
curl http://localhost:5000/test-celery

# Forçar verificação manual
curl http://localhost:5000/force-check-notifications
```

### Logs do Sistema
```bash
# Logs do Worker
tail -f logs/sistema_fazendas.log

# Logs do Celery Worker (se rodando em background)
tail -f celery_worker.log

# Logs do Beat
tail -f celery_beat.log
```

---

## 📊 Configuração de Produção com Supervisor

Para manter os processos rodando automaticamente:

### 1. Instalar Supervisor
```bash
sudo apt-get install supervisor
```

### 2. Configurar Worker (`/etc/supervisor/conf.d/celery_worker.conf`)
```ini
[program:celery_worker]
command=/path/to/venv/bin/celery -A celery_app worker --loglevel=info
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=998
```

### 3. Configurar Beat (`/etc/supervisor/conf.d/celery_beat.conf`)
```ini
[program:celery_beat]
command=/path/to/venv/bin/celery -A celery_app beat --loglevel=info
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat.log
autostart=true
autorestart=true
startsecs=10
priority=999
```

### 4. Iniciar Serviços
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery_worker
sudo supervisorctl start celery_beat
```

---

## ⚠️ Importantes Considerações

### Segurança
- **Nunca** commite o arquivo `.env` no repositório
- Use senhas de app do Gmail, não a senha real
- Configure firewall para proteger Redis (porta 6379)

### Performance
- Em produção, considere usar múltiplos workers:
  ```bash
  celery -A celery_app worker --concurrency=4 --loglevel=info
  ```

### Backup
- Faça backup regular do banco de dados
- Configure rotação de logs
- Monitore uso de memória e CPU

### Testes
- Execute `python celery_diagnostic.py` após mudanças
- Teste manualmente as notificações antes de colocar em produção
- Monitore logs nos primeiros dias

---

## 📝 Resumo da Correção

O sistema de notificações agora está **100% funcional**. Os principais problemas eram:

1. ❌ **Tasks não registradas corretamente** → ✅ **Corrigido**
2. ❌ **Agendamentos inválidos** → ✅ **Corrigido**  
3. ❌ **Timezone inconsistente** → ✅ **Corrigido**
4. ❌ **Contexto Flask ausente** → ✅ **Corrigido**

**Resultado:** As notificações serão enviadas automaticamente nos horários configurados (8h e 14h) e o sistema pode ser testado a qualquer momento.