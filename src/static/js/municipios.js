// Arquivo para gerenciar a auto-sugestão de municípios
document.addEventListener('DOMContentLoaded', function() {
    // Elementos do formulário
    const estadoSelect = document.getElementById('estado');
    const municipioInput = document.getElementById('municipio');
    
    // Criar elementos para a lista de sugestões
    const sugestoesContainer = document.createElement('div');
    sugestoesContainer.className = 'sugestoes-container';
    sugestoesContainer.style.display = 'none';
    sugestoesContainer.style.position = 'absolute';
    sugestoesContainer.style.width = municipioInput.offsetWidth + 'px';
    sugestoesContainer.style.maxHeight = '200px';
    sugestoesContainer.style.overflowY = 'auto';
    sugestoesContainer.style.border = '1px solid #ced4da';
    sugestoesContainer.style.borderRadius = '0.25rem';
    sugestoesContainer.style.backgroundColor = '#fff';
    sugestoesContainer.style.zIndex = '1000';
    sugestoesContainer.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
    
    // Inserir o container de sugestões após o input de município
    municipioInput.parentNode.insertBefore(sugestoesContainer, municipioInput.nextSibling);
    
    // Cache para armazenar municípios por estado
    const municipiosPorEstado = {};
    
    // Municípios mais comuns por estado (fallback)
    const municipiosFallback = {
        'SP': [
            {nome: 'São Paulo'}, {nome: 'Campinas'}, {nome: 'Santos'}, 
            {nome: 'Ribeirão Preto'}, {nome: 'Sorocaba'}, {nome: 'São José dos Campos'},
            {nome: 'Piracicaba'}, {nome: 'Bauru'}, {nome: 'Jundiaí'}, {nome: 'Franca'}
        ],
        'RJ': [
            {nome: 'Rio de Janeiro'}, {nome: 'Niterói'}, {nome: 'Campos dos Goytacazes'},
            {nome: 'Volta Redonda'}, {nome: 'Petrópolis'}, {nome: 'Nova Iguaçu'}
        ],
        'MG': [
            {nome: 'Belo Horizonte'}, {nome: 'Uberlândia'}, {nome: 'Contagem'},
            {nome: 'Juiz de Fora'}, {nome: 'Betim'}, {nome: 'Montes Claros'}
        ],
        'RS': [
            {nome: 'Porto Alegre'}, {nome: 'Caxias do Sul'}, {nome: 'Pelotas'},
            {nome: 'Canoas'}, {nome: 'Santa Maria'}, {nome: 'Gravataí'}
        ],
        'PR': [
            {nome: 'Curitiba'}, {nome: 'Londrina'}, {nome: 'Maringá'},
            {nome: 'Ponta Grossa'}, {nome: 'Cascavel'}, {nome: 'São José dos Pinhais'}
        ],
        'SC': [
            {nome: 'Florianópolis'}, {nome: 'Joinville'}, {nome: 'Blumenau'},
            {nome: 'São José'}, {nome: 'Criciúma'}, {nome: 'Chapecó'}
        ],
        'GO': [
            {nome: 'Goiânia'}, {nome: 'Aparecida de Goiânia'}, {nome: 'Anápolis'},
            {nome: 'Rio Verde'}, {nome: 'Luziânia'}, {nome: 'Águas Lindas de Goiás'}
        ],
        'MT': [
            {nome: 'Cuiabá'}, {nome: 'Várzea Grande'}, {nome: 'Rondonópolis'},
            {nome: 'Sinop'}, {nome: 'Tangará da Serra'}, {nome: 'Cáceres'}
        ],
        'MS': [
            {nome: 'Campo Grande'}, {nome: 'Dourados'}, {nome: 'Três Lagoas'},
            {nome: 'Corumbá'}, {nome: 'Ponta Porã'}, {nome: 'Naviraí'}
        ],
        'BA': [
            {nome: 'Salvador'}, {nome: 'Feira de Santana'}, {nome: 'Vitória da Conquista'},
            {nome: 'Camaçari'}, {nome: 'Juazeiro'}, {nome: 'Ilhéus'}
        ]
    };

    // Função para buscar municípios da API
    async function buscarMunicipios(siglaUF) {
        // Verificar se já temos os municípios em cache
        if (municipiosPorEstado[siglaUF]) {
            return municipiosPorEstado[siglaUF];
        }
        
        try {
            const response = await fetch(`https://brasilapi.com.br/api/ibge/municipios/v1/${siglaUF}`, {
                timeout: 5000,
                headers: {
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (compatible; Gestao-Agro/1.0)'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const municipios = await response.json();
            // Armazenar em cache
            municipiosPorEstado[siglaUF] = municipios;
            return municipios;
        } catch (error) {
            console.warn('Erro ao buscar municípios da API:', error);
            console.info('Usando lista de municípios offline para', siglaUF);
            
            // Fallback para lista local
            const municipiosFallbackUF = municipiosFallback[siglaUF] || [];
            municipiosPorEstado[siglaUF] = municipiosFallbackUF;
            return municipiosFallbackUF;
        }
    }
    
    // Função para exibir sugestões
    function exibirSugestoes(municipios, filtro) {
        // Limpar sugestões anteriores
        sugestoesContainer.innerHTML = '';
        
        // Filtrar municípios pelo texto digitado
        const municipiosFiltrados = municipios.filter(municipio => 
            municipio.nome.toLowerCase().includes(filtro.toLowerCase())
        ).slice(0, 10); // Limitar a 10 sugestões
        
        if (municipiosFiltrados.length === 0) {
            // Mostrar mensagem quando não há sugestões
            if (filtro.length > 2) {
                const mensagem = document.createElement('div');
                mensagem.className = 'sugestao-item sugestao-vazia';
                mensagem.textContent = 'Nenhum município encontrado. Digite o nome manualmente.';
                mensagem.style.padding = '8px 12px';
                mensagem.style.color = '#6c757d';
                mensagem.style.fontStyle = 'italic';
                sugestoesContainer.appendChild(mensagem);
                sugestoesContainer.style.display = 'block';
                return;
            } else {
                sugestoesContainer.style.display = 'none';
                return;
            }
        }
        
        // Criar elementos para cada sugestão
        municipiosFiltrados.forEach(municipio => {
            const sugestao = document.createElement('div');
            sugestao.className = 'sugestao-item';
            sugestao.textContent = municipio.nome;
            sugestao.style.padding = '8px 12px';
            sugestao.style.cursor = 'pointer';
            sugestao.style.borderBottom = '1px solid #e9ecef';
            
            // Destacar ao passar o mouse
            sugestao.addEventListener('mouseover', function() {
                this.style.backgroundColor = '#f8f9fa';
            });
            
            sugestao.addEventListener('mouseout', function() {
                this.style.backgroundColor = 'transparent';
            });
            
            // Selecionar município ao clicar
            sugestao.addEventListener('click', function() {
                municipioInput.value = municipio.nome;
                sugestoesContainer.style.display = 'none';
            });
            
            sugestoesContainer.appendChild(sugestao);
        });
        
        // Exibir container de sugestões
        sugestoesContainer.style.display = 'block';
    }
    
    // Evento ao mudar o estado
    estadoSelect.addEventListener('change', async function() {
        const siglaUF = this.value;
        if (!siglaUF) return;
        
        // Limpar campo de município
        municipioInput.value = '';
        
        // Buscar municípios do estado selecionado
        const municipios = await buscarMunicipios(siglaUF);
        
        // Focar no campo de município para facilitar a digitação
        municipioInput.focus();
    });
    
    // Evento ao digitar no campo de município
    municipioInput.addEventListener('input', async function() {
        const siglaUF = estadoSelect.value;
        if (!siglaUF) return;
        
        const filtro = this.value;
        
        // Buscar municípios do estado selecionado
        const municipios = await buscarMunicipios(siglaUF);
        
        // Exibir sugestões filtradas
        exibirSugestoes(municipios, filtro);
    });
    
    // Fechar sugestões ao clicar fora
    document.addEventListener('click', function(event) {
        if (event.target !== municipioInput && event.target !== sugestoesContainer) {
            sugestoesContainer.style.display = 'none';
        }
    });
    
    // Navegação pelo teclado nas sugestões
    municipioInput.addEventListener('keydown', function(event) {
        const sugestoes = sugestoesContainer.querySelectorAll('.sugestao-item');
        if (!sugestoes.length) return;
        
        const ativo = sugestoesContainer.querySelector('.sugestao-item.ativo');
        
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                if (!ativo) {
                    sugestoes[0].classList.add('ativo');
                    sugestoes[0].style.backgroundColor = '#e9ecef';
                } else {
                    const index = Array.from(sugestoes).indexOf(ativo);
                    if (index < sugestoes.length - 1) {
                        ativo.classList.remove('ativo');
                        ativo.style.backgroundColor = 'transparent';
                        sugestoes[index + 1].classList.add('ativo');
                        sugestoes[index + 1].style.backgroundColor = '#e9ecef';
                    }
                }
                break;
                
            case 'ArrowUp':
                event.preventDefault();
                if (ativo) {
                    const index = Array.from(sugestoes).indexOf(ativo);
                    if (index > 0) {
                        ativo.classList.remove('ativo');
                        ativo.style.backgroundColor = 'transparent';
                        sugestoes[index - 1].classList.add('ativo');
                        sugestoes[index - 1].style.backgroundColor = '#e9ecef';
                    }
                }
                break;
                
            case 'Enter':
                if (ativo) {
                    event.preventDefault();
                    municipioInput.value = ativo.textContent;
                    sugestoesContainer.style.display = 'none';
                }
                break;
                
            case 'Escape':
                sugestoesContainer.style.display = 'none';
                break;
        }
    });
});
