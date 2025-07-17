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
    

    // Dados de fallback offline para os principais municípios brasileiros
    const municipiosFallback = {
        'SP': [
            {nome: 'São Paulo'}, {nome: 'Campinas'}, {nome: 'Santos'}, {nome: 'Ribeirão Preto'},
            {nome: 'São José dos Campos'}, {nome: 'Sorocaba'}, {nome: 'Osasco'}, {nome: 'Piracicaba'},
            {nome: 'Bauru'}, {nome: 'São Carlos'}, {nome: 'Marília'}, {nome: 'Taubaté'},
            {nome: 'Limeira'}, {nome: 'Presidente Prudente'}, {nome: 'Araçatuba'}, {nome: 'Araraquara'},
            {nome: 'Franca'}, {nome: 'Americana'}, {nome: 'Botucatu'}, {nome: 'Jacareí'}
        ],
        'RJ': [
            {nome: 'Rio de Janeiro'}, {nome: 'Niterói'}, {nome: 'Nova Iguaçu'}, {nome: 'São Gonçalo'},
            {nome: 'Duque de Caxias'}, {nome: 'Campos dos Goytacazes'}, {nome: 'Petrópolis'},
            {nome: 'Volta Redonda'}, {nome: 'Magé'}, {nome: 'Barra Mansa'}, {nome: 'Nova Friburgo'},
            {nome: 'Cabo Frio'}, {nome: 'Angra dos Reis'}, {nome: 'Resende'}, {nome: 'Teresópolis'}
        ],
        'MG': [
            {nome: 'Belo Horizonte'}, {nome: 'Uberlândia'}, {nome: 'Contagem'}, {nome: 'Juiz de Fora'},
            {nome: 'Montes Claros'}, {nome: 'Uberaba'}, {nome: 'Governador Valadares'}, {nome: 'Betim'},
            {nome: 'Ipatinga'}, {nome: 'Sete Lagoas'}, {nome: 'Divinópolis'}, {nome: 'Santa Luzia'},
            {nome: 'Ribeirão das Neves'}, {nome: 'Patos de Minas'}, {nome: 'Poços de Caldas'}
        ],
        'RS': [
            {nome: 'Porto Alegre'}, {nome: 'Caxias do Sul'}, {nome: 'Canoas'}, {nome: 'Pelotas'},
            {nome: 'Santa Maria'}, {nome: 'Gravataí'}, {nome: 'Viamão'}, {nome: 'Novo Hamburgo'},
            {nome: 'São Leopoldo'}, {nome: 'Rio Grande'}, {nome: 'Alvorada'}, {nome: 'Passo Fundo'},
            {nome: 'Sapucaia do Sul'}, {nome: 'Uruguaiana'}, {nome: 'Santa Cruz do Sul'}
        ],
        'PR': [
            {nome: 'Curitiba'}, {nome: 'Londrina'}, {nome: 'Maringá'}, {nome: 'Ponta Grossa'},
            {nome: 'Cascavel'}, {nome: 'São José dos Pinhais'}, {nome: 'Foz do Iguaçu'},
            {nome: 'Colombo'}, {nome: 'Guarapuava'}, {nome: 'Paranaguá'}, {nome: 'Araucária'},
            {nome: 'Toledo'}, {nome: 'Apucarana'}, {nome: 'Pinhais'}, {nome: 'Campo Largo'}
        ],
        'SC': [
            {nome: 'Florianópolis'}, {nome: 'Joinville'}, {nome: 'Blumenau'}, {nome: 'São José'},
            {nome: 'Criciúma'}, {nome: 'Chapecó'}, {nome: 'Itajaí'}, {nome: 'Lages'},
            {nome: 'Jaraguá do Sul'}, {nome: 'Palhoça'}, {nome: 'Balneário Camboriú'},
            {nome: 'Brusque'}, {nome: 'Tubarão'}, {nome: 'São Bento do Sul'}, {nome: 'Caçador'}
        ],
        'GO': [
            {nome: 'Goiânia'}, {nome: 'Aparecida de Goiânia'}, {nome: 'Anápolis'}, {nome: 'Rio Verde'},
            {nome: 'Luziânia'}, {nome: 'Águas Lindas de Goiás'}, {nome: 'Valparaíso de Goiás'},
            {nome: 'Trindade'}, {nome: 'Formosa'}, {nome: 'Novo Gama'}, {nome: 'Itumbiara'},
            {nome: 'Senador Canedo'}, {nome: 'Catalão'}, {nome: 'Jataí'}, {nome: 'Planaltina'}
        ],
        'MT': [
            {nome: 'Cuiabá'}, {nome: 'Várzea Grande'}, {nome: 'Rondonópolis'}, {nome: 'Sinop'},
            {nome: 'Tangará da Serra'}, {nome: 'Cáceres'}, {nome: 'Sorriso'}, {nome: 'Lucas do Rio Verde'},
            {nome: 'Barra do Garças'}, {nome: 'Primavera do Leste'}, {nome: 'Alta Floresta'},
            {nome: 'Poxoréu'}, {nome: 'Nova Mutum'}, {nome: 'Diamantino'}, {nome: 'Juína'}
        ],
        'MS': [
            {nome: 'Campo Grande'}, {nome: 'Dourados'}, {nome: 'Três Lagoas'}, {nome: 'Corumbá'},
            {nome: 'Ponta Porã'}, {nome: 'Naviraí'}, {nome: 'Nova Andradina'}, {nome: 'Aquidauana'},
            {nome: 'Sidrolândia'}, {nome: 'Maracaju'}, {nome: 'São Gabriel do Oeste'},
            {nome: 'Coxim'}, {nome: 'Chapadão do Sul'}, {nome: 'Amambai'}, {nome: 'Paranaíba'}
        ],
        'BA': [
            {nome: 'Salvador'}, {nome: 'Feira de Santana'}, {nome: 'Vitória da Conquista'},
            {nome: 'Camaçari'}, {nome: 'Juazeiro'}, {nome: 'Itabuna'}, {nome: 'Lauro de Freitas'},
            {nome: 'Ilhéus'}, {nome: 'Jequié'}, {nome: 'Teixeira de Freitas'}, {nome: 'Alagoinhas'},
            {nome: 'Porto Seguro'}, {nome: 'Simões Filho'}, {nome: 'Paulo Afonso'}, {nome: 'Eunápolis'}
        ]
    };

    // Função para buscar municípios da API com fallback offline
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

                throw new Error('Erro ao buscar municípios da API');

            }
            
            const municipios = await response.json();
            // Armazenar em cache
            municipiosPorEstado[siglaUF] = municipios;
            return municipios;
        } catch (error) {

            console.warn('Erro ao buscar municípios da API, usando dados offline:', error);
            
            // Usar dados de fallback se disponíveis
            const municipiosFallbackUF = municipiosFallback[siglaUF] || [];
            
            // Armazenar em cache mesmo sendo fallback
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
