# Guia do Usuário - Sistema de Gestão de Fazendas

Este guia fornece instruções detalhadas para utilizar o Sistema de Gestão de Fazendas.

## Índice

1. [Primeiros Passos](#primeiros-passos)
2. [Cadastro de Pessoas](#cadastro-de-pessoas)
3. [Cadastro de Fazendas/Áreas](#cadastro-de-fazendas-áreas)
4. [Gestão de Documentos](#gestão-de-documentos)
5. [Sistema de Notificações](#sistema-de-notificações)
6. [Dashboard e Relatórios](#dashboard-e-relatórios)
7. [Dicas e Truques](#dicas-e-truques)
8. [Solução de Problemas](#solução-de-problemas)

## Primeiros Passos

### Acessando o Sistema

1. Após a instalação, acesse o sistema através do navegador:
   - Instalação local: `http://localhost:5000`
   - Instalação no Heroku: `https://nome-do-seu-app.herokuapp.com`

2. Você será direcionado para o Dashboard principal, que exibe um resumo das informações do sistema.

## Cadastro de Pessoas

### Adicionar Nova Pessoa

1. No menu lateral, clique em "Pessoas"
2. Clique no botão "Nova Pessoa"
3. Preencha os campos obrigatórios:
   - Nome
   - CPF/CNPJ (formato: 123.456.789-00 ou 12.345.678/0001-90)
4. Preencha os campos opcionais:
   - E-mail
   - Telefone
   - Endereço
5. Clique em "Salvar"

### Editar Pessoa

1. Na lista de pessoas, clique no botão "Editar" na linha correspondente
2. Atualize os campos desejados
3. Clique em "Salvar"

### Associar Pessoa a Fazendas

1. Na lista de pessoas, clique no botão "Ver Fazendas" na linha correspondente
2. Na página de fazendas da pessoa, clique em "Associar Fazenda"
3. Selecione a fazenda desejada na lista
4. Clique em "Associar"

## Cadastro de Fazendas/Áreas

### Adicionar Nova Fazenda/Área

1. No menu lateral, clique em "Fazendas/Áreas"
2. Clique no botão "Nova Fazenda/Área"
3. Preencha os campos obrigatórios:
   - Nome
   - Matrícula (número único)
   - Tamanho Total (em hectares)
   - Área Consolidada (em hectares)
   - Tipo de Posse (Própria, Arrendada, Comodato ou Posse)
   - Estado (selecione da lista)
   - Município (selecione da lista após escolher o estado)
4. Preencha os campos opcionais:
   - Número do Recibo do CAR
5. Clique em "Salvar"

### Editar Fazenda/Área

1. Na lista de fazendas, clique no botão "Editar" na linha correspondente
2. Atualize os campos desejados
3. Clique em "Salvar"

### Visualizar Pessoas Associadas

1. Na lista de fazendas, clique no botão "Ver Pessoas" na linha correspondente
2. A página exibirá todas as pessoas associadas à fazenda

## Gestão de Documentos

### Adicionar Novo Documento

1. No menu lateral, clique em "Documentos"
2. Clique no botão "Novo Documento"
3. Selecione o tipo de entidade relacionada:
   - Fazenda/Área
   - Pessoa
4. Selecione a entidade específica na lista
5. Preencha os campos obrigatórios:
   - Nome do documento
   - Tipo (Certidões, Contratos, Documentos da Área, Outros)
   - Data de Emissão
6. Preencha os campos opcionais:
   - Data de Vencimento
   - E-mails para notificação (separados por vírgula)
   - Prazos de notificação (selecione um ou mais: 30, 15, 7, 3, 1 dias)
7. Clique em "Testar E-mail" para verificar se as notificações estão configuradas corretamente
8. Clique em "Salvar"

### Editar Documento

1. Na lista de documentos, clique no botão "Editar" na linha correspondente
2. Atualize os campos desejados
3. Clique em "Salvar"

### Visualizar Documentos por Entidade

1. Na lista de fazendas ou pessoas, clique no botão "Ver Documentos" na linha correspondente
2. A página exibirá todos os documentos associados à entidade selecionada

## Sistema de Notificações

### Configurar Notificações por E-mail

1. Ao cadastrar ou editar um documento, informe os e-mails que devem receber notificações
   - Você pode adicionar múltiplos e-mails separados por vírgula
2. Selecione os prazos de notificação desejados:
   - 30 dias antes do vencimento
   - 15 dias antes do vencimento
   - 7 dias antes do vencimento
   - 3 dias antes do vencimento
   - 1 dia antes do vencimento

### Testar Notificações

1. Ao cadastrar ou editar um documento, clique no botão "Testar E-mail"
2. Um e-mail de teste será enviado para os endereços informados
3. Verifique se o e-mail foi recebido corretamente

### Enviar Notificações Manualmente

1. No menu lateral, clique em "Vencimentos"
2. Clique no botão "Enviar Notificações"
3. Confirme a ação
4. O sistema enviará e-mails para todos os documentos que estão dentro dos prazos de notificação configurados

## Dashboard e Relatórios

### Dashboard Principal

O dashboard principal exibe:
- Total de pessoas cadastradas
- Total de fazendas/áreas cadastradas
- Total de documentos cadastrados
- Documentos vencidos
- Documentos próximos do vencimento

### Relatório de Vencimentos

1. No menu lateral, clique em "Vencimentos"
2. A página exibirá:
   - Documentos já vencidos
   - Documentos próximos do vencimento, agrupados por prazo

## Dicas e Truques

### Filtros Rápidos

- Utilize a caixa de pesquisa no topo de cada lista para filtrar resultados
- Clique nos cabeçalhos das colunas para ordenar os dados

### Associações Eficientes

- Ao cadastrar uma nova pessoa, você pode associá-la a fazendas existentes diretamente na página de detalhes
- Da mesma forma, ao cadastrar uma nova fazenda, você pode associá-la a pessoas existentes

### Notificações Eficientes

- Configure múltiplos e-mails para receber notificações de documentos importantes
- Utilize diferentes prazos de notificação para documentos críticos

## Solução de Problemas

### Problemas Comuns

- **Erro ao salvar documento**: Verifique se todos os campos obrigatórios foram preenchidos
- **E-mail de teste não recebido**: Verifique se o endereço de e-mail está correto e se o servidor SMTP está configurado adequadamente
- **Erro ao associar pessoa a fazenda**: Verifique se ambas as entidades existem no sistema

### Suporte

Para obter suporte adicional, entre em contato com o administrador do sistema ou consulte a documentação técnica em `docs/DEPLOYMENT.md`.
