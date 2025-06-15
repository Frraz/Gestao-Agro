#!/bin/bash

# Script para executar testes
echo "Executando testes do sistema de gestão agro..."

# Ativar ambiente virtual se existir
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Executar testes unitários
python -m pytest tests/ -v

# Executar testes com unittest se pytest não estiver disponível
if [ $? -ne 0 ]; then
    echo "Pytest não encontrado, executando com unittest..."
    python -m unittest discover tests/ -v
fi

echo "Testes concluídos!"

