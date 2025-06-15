#!/bin/bash

echo "=== 🚜 Iniciando testes do Sistema de Gestão de Fazendas com MySQL ==="

read -sp "Digite a senha do MySQL: " MYSQL_PASSWORD
echo

# Verifica se o MySQL está ativo
if mysqladmin ping -u root -p"$MYSQL_PASSWORD" &> /dev/null; then
  echo "mysqld is alive"
else
  echo "❌ MySQL não está ativo. Verifique se o serviço está rodando e a senha está correta."
  exit 1
fi

echo "🌐 Verificando status da API..."

# Inicia a API Flask em segundo plano
echo "🚀 Iniciando a aplicação..."
python3 src/main.py &
APP_PID=$!
echo "🆔 Aplicação iniciada com PID: $APP_PID"

# Aguarda a API subir
sleep 3

BASE_URL="http://localhost:5000"

echo "=== ✅ Executando testes de fluxos ==="

# Função para gerar CPF válido
gerar_cpf_valido() {
  base=$(printf "%09d" $((RANDOM % 1000000000)))
  soma=0
  for ((i=0; i<9; i++)); do
    soma=$((soma + ${base:i:1} * (10 - i)))
  done
  resto=$((soma % 11))
  dv1=$((resto < 2 ? 0 : 11 - resto))

  soma=0
  for ((i=0; i<9; i++)); do
    soma=$((soma + ${base:i:1} * (11 - i)))
  done
  soma=$((soma + dv1 * 2))
  resto=$((soma % 11))
  dv2=$((resto < 2 ? 0 : 11 - resto))

  echo "$base$dv1$dv2"
}

# Teste 1: Verifica se a API está respondendo
echo "🧪 Teste 1: Verificando se a API está respondendo..."
if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" | grep -q "200"; then
  echo "✅ API está respondendo corretamente"
else
  echo "❌ API não está respondendo"
fi

# Teste 2: Cria uma pessoa
echo "🧪 Teste 2: Criando uma pessoa..."
CPF=$(gerar_cpf_valido)
RESPONSE=$(curl -s -X POST "$BASE_URL/api/pessoas/" -H "Content-Type: application/json" \
  -d "{\"nome\": \"João Teste\", \"cpf_cnpj\": \"$CPF\", \"telefone\": \"(11) 98765-4321\", \"email\": \"joao${CPF}@teste.com\"}")
ID_PESSOA=$(echo "$RESPONSE" | jq -r '.id')

if [[ "$ID_PESSOA" != "null" ]]; then
  echo "✅ Pessoa criada com sucesso. ID: $ID_PESSOA"
else
  echo "❌ Falha ao criar pessoa"
  echo "$RESPONSE"
fi

# Teste 3: Cria uma fazenda
echo "🧪 Teste 3: Criando uma fazenda..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/fazendas/" -H "Content-Type: application/json" \
  -d '{"nome": "Fazenda Teste", "matricula": "12345", "recibo_car": "CAR12345", "tamanho_total": 1000.0, "area_consolidada": 500.0, "estado": "SP", "municipio": "São Paulo", "tipo_posse": "Própria"}')
ID_FAZENDA=$(echo "$RESPONSE" | jq -r '.id')

if [[ "$ID_FAZENDA" != "null" ]]; then
  echo "✅ Fazenda criada com sucesso. ID: $ID_FAZENDA"
else
  echo "❌ Falha ao criar fazenda"
  echo "$RESPONSE"
fi

# Teste 4: Associa pessoa à fazenda
echo "🧪 Teste 4: Associando pessoa à fazenda..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/pessoas/$ID_PESSOA/fazendas/$ID_FAZENDA")

if echo "$RESPONSE" | grep -q "associada"; then
  echo "✅ Pessoa associada à fazenda com sucesso"
else
  echo "❌ Falha na associação"
  echo "$RESPONSE"
fi

# Teste 5: Criando um documento com dados reais
echo "🧪 Teste 5: Criando um documento com notificações..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/documentos/" -H "Content-Type: application/json" \
  -d "{
    \"nome\": \"Licença Ambiental - IBAMA\",
    \"tipo\": \"Documentos da Área\",
    \"numero\": \"LIC2024-998\",
    \"orgao_emissor\": \"IBAMA\",
    \"data_emissao\": \"2024-06-01\",
    \"data_validade\": \"2024-07-01\",
    \"tipo_entidade\": \"PESSOA\",
    \"pessoa_id\": $ID_PESSOA,
    \"emails_notificacao\": [\"joao@teste.com\", \"admin@fazenda.com\"],
    \"prazos_notificacao\": [30, 15, 5]
  }")
ID_DOCUMENTO=$(echo "$RESPONSE" | jq -r '.id')

if [[ "$ID_DOCUMENTO" != "null" ]]; then
  echo "✅ Documento criado com sucesso. ID: $ID_DOCUMENTO"
else
  echo "❌ Falha ao criar documento"
  echo "$RESPONSE"
fi


# Teste 6: Verificando documentos vencidos
echo "🧪 Teste 6: Verificando documentos vencidos..."
RESPONSE=$(curl -s "$BASE_URL/api/documentos/vencidos")
if echo "$RESPONSE" | jq '.' &> /dev/null; then
  echo "✅ Consulta de documentos vencidos realizada"
else
  echo "❌ Falha na consulta de documentos vencidos"
fi

# Teste 7: Atualizando uma fazenda
echo "🧪 Teste 7: Atualizando uma fazenda..."
RESPONSE=$(curl -s -X PUT "$BASE_URL/api/fazendas/$ID_FAZENDA" -H "Content-Type: application/json" \
  -d '{"nome": "Fazenda Teste Atualizada", "matricula": "12345", "recibo_car": "CAR12345", "tamanho_total": 1000.0, "area_consolidada": 600.0, "estado": "SP", "municipio": "São Paulo", "tipo_posse": "Própria"}')

if echo "$RESPONSE" | jq '.' &> /dev/null; then
  echo "✅ Fazenda atualizada com sucesso"
else
  echo "❌ Falha ao atualizar fazenda"
fi

# Teste 8: Verificando cálculo automático de tamanho disponível (corrigido com valor 400.0)
echo "🧪 Teste 8: Verificando cálculo automático de tamanho disponível..."
RESPONSE=$(curl -s "$BASE_URL/api/fazendas/$ID_FAZENDA")
TAM_DISPONIVEL=$(echo "$RESPONSE" | jq -r '.tamanho_disponivel')
if [[ "$TAM_DISPONIVEL" == "400.0" ]]; then
  echo "✅ Cálculo automático correto de tamanho disponível: $TAM_DISPONIVEL"
else
  echo "❌ Falha no cálculo de tamanho disponível. Valor: $TAM_DISPONIVEL"
fi

# Teste 9: Verificando dados cadastrados
echo "=== 📋 Teste 9: Verificando dados cadastrados no banco ==="

echo "🔍 Verificando pessoa..."
curl -s "$BASE_URL/api/pessoas/$ID_PESSOA" | jq '.'

echo "🔍 Verificando fazenda..."
curl -s "$BASE_URL/api/fazendas/$ID_FAZENDA" | jq '.'

echo "🔍 Verificando associação pessoa-fazenda..."
curl -s "$BASE_URL/api/pessoas/$ID_PESSOA/fazendas" | jq '.'

echo "🔍 Verificando documento..."
if [[ "$ID_DOCUMENTO" != "null" ]]; then
  curl -s "$BASE_URL/api/documentos/$ID_DOCUMENTO" | jq '.'
else
  echo "❌ Documento não encontrado"
fi

# Limpeza
read -p "🧹 Deseja limpar os dados de teste? (s/n) " RESPOSTA
if [[ "$RESPOSTA" == "s" ]]; then
  echo "🗑️ Limpando dados de teste..."
  [[ "$ID_DOCUMENTO" != "null" ]] && curl -s -X DELETE "$BASE_URL/api/documentos/$ID_DOCUMENTO"
  curl -s -X DELETE "$BASE_URL/api/pessoas/$ID_PESSOA/fazendas/$ID_FAZENDA"
  curl -s -X DELETE "$BASE_URL/api/fazendas/$ID_FAZENDA"
  curl -s -X DELETE "$BASE_URL/api/pessoas/$ID_PESSOA"
  echo "✅ Dados de teste removidos com sucesso"
fi

# Encerra o processo da aplicação
kill "$APP_PID"
echo "🛑 Aplicação encerrada (PID $APP_PID)"
echo "✅ Testes finalizados. Verifique os resultados acima."
