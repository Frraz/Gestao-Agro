// /src/static/js/script.js

$(document).ready(function() {
    // Inicialização de tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Inicialização de popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });

    // Confirmação de exclusão
    $('.btn-delete').on('click', function(e) {
        if (!confirm('Tem certeza que deseja excluir este item? Esta ação não pode ser desfeita.')) {
            e.preventDefault();
        }
    });

    // Máscara para CPF/CNPJ
    $('.cpf-cnpj-mask').on('input', function() {
        let value = $(this).val().replace(/\D/g, '');
        
        if (value.length <= 11) {
            // CPF
            value = value.replace(/(\d{3})(\d)/, '$1.$2');
            value = value.replace(/(\d{3})(\d)/, '$1.$2');
            value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
        } else {
            // CNPJ
            value = value.replace(/^(\d{2})(\d)/, '$1.$2');
            value = value.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
            value = value.replace(/\.(\d{3})(\d)/, '.$1/$2');
            value = value.replace(/(\d{4})(\d)/, '$1-$2');
        }
        
        $(this).val(value);
    });

    // Máscara para valores monetários
    $('.money-mask').on('input', function() {
        let value = $(this).val().replace(/\D/g, '');
        value = (value / 100).toFixed(2) + '';
        value = value.replace(".", ",");
        value = value.replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");
        $(this).val('R$ ' + value);
    });

    // Validação de formulários
    $('.needs-validation').on('submit', function(event) {
        if (!this.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        $(this).addClass('was-validated');
    });

    // Filtro de tabelas
    $("#tableSearch").on("keyup", function() {
        var value = $(this).val().toLowerCase();
        $("table tbody tr").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    // Loading states para botões
    $('.btn-loading').on('click', function() {
        var $btn = $(this);
        var originalText = $btn.html();
        
        $btn.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Carregando...');
        $btn.prop('disabled', true);
        
        // Simular carregamento (remover em produção)
        setTimeout(function() {
            $btn.html(originalText);
            $btn.prop('disabled', false);
        }, 2000);
    });

    // Auto-save para formulários (opcional)
    $('.auto-save').on('change', function() {
        var $form = $(this).closest('form');
        var formData = $form.serialize();
        
        // Salvar no localStorage
        localStorage.setItem('form_' + $form.attr('id'), formData);
        
        // Mostrar indicador de salvamento
        showToast('Dados salvos automaticamente', 'success');
    });

    // Carregar dados salvos automaticamente
    $('.auto-save').each(function() {
        var $form = $(this).closest('form');
        var savedData = localStorage.getItem('form_' + $form.attr('id'));
        
        if (savedData) {
            // Restaurar dados do formulário
            var params = new URLSearchParams(savedData);
            params.forEach(function(value, key) {
                $form.find('[name="' + key + '"]').val(value);
            });
        }
    });

    // Função para mostrar toasts
    function showToast(message, type = 'info') {
        var toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        // Criar container de toasts se não existir
        if (!$('#toast-container').length) {
            $('body').append('<div id="toast-container" class="toast-container position-fixed bottom-0 end-0 p-3"></div>');
        }
        
        var $toast = $(toastHtml);
        $('#toast-container').append($toast);
        
        var toast = new bootstrap.Toast($toast[0]);
        toast.show();
        
        // Remover toast após ser ocultado
        $toast.on('hidden.bs.toast', function() {
            $(this).remove();
        });
    }

    // Smooth scroll para âncoras
    $('a[href^="#"]').on('click', function(event) {
        var target = $(this.getAttribute('href'));
        if (target.length) {
            event.preventDefault();
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 100
            }, 1000);
        }
    });

    // Lazy loading para imagens
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }

    // Detectar modo escuro do sistema
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        if (!localStorage.getItem('theme')) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
    }

    // Escutar mudanças no modo escuro do sistema
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }
    });

    // Melhorar acessibilidade - navegação por teclado
    $(document).on('keydown', function(e) {
        // ESC para fechar modais
        if (e.key === 'Escape') {
            $('.modal.show').modal('hide');
        }
        
        // Enter para submeter formulários quando focado em input
        if (e.key === 'Enter' && $(e.target).is('input:not([type="submit"])')) {
            var $form = $(e.target).closest('form');
            if ($form.length) {
                $form.find('[type="submit"]').first().click();
            }
        }
    });

    // Adicionar indicadores de carregamento para requisições AJAX
    $(document).ajaxStart(function() {
        $('body').addClass('loading');
    }).ajaxStop(function() {
        $('body').removeClass('loading');
    });
});

// Funções globais úteis
window.formatCurrency = function(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
};

window.formatDate = function(date) {
    return new Intl.DateTimeFormat('pt-BR').format(new Date(date));
};

window.debounce = function(func, wait, immediate) {
    var timeout;
    return function() {
        var context = this, args = arguments;
        var later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
};

// === BUSCA E SELEÇÃO DE PESSOAS ===

// Enter no campo de busca faz buscar (e previne submit)
$('#buscaPessoa').on('keydown', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        window.buscarPessoas();
    }
});

// Seleção robusta com Set
var pessoasSelecionadasIds = new Set();

// Inicializa com badges já renderizados
$(document).ready(function() {
    $('#pessoasSelecionadas [data-pessoa-id]').each(function() {
        pessoasSelecionadasIds.add(String($(this).data('pessoa-id')));
    });
});

$(document).on('click', '.selecionar-pessoa', function() {
    var id = String($(this).data('id'));
    var nome = $(this).data('nome');
    var cpfCnpj = $(this).data('cpf-cnpj');
    if (!pessoasSelecionadasIds.has(id)) {
        pessoasSelecionadasIds.add(id);
        $('#pessoasSelecionadas').append(
            `<div class="pessoa-selecionada badge bg-primary me-2 mb-2 p-2" data-pessoa-id="${id}">
                ${nome} (${cpfCnpj})
                <button type="button" class="btn-close btn-close-white ms-2 remover-pessoa" data-id="${id}"></button>
                <input type="hidden" name="pessoas_ids" value="${id}">
            </div>`
        );
    }
    $('#resultadosBusca').empty().hide();
    $('#buscaPessoa').val('');
});

// Remover pessoa do Set ao remover badge
$(document).on('click', '.remover-pessoa', function() {
    var id = String($(this).data('id'));
    pessoasSelecionadasIds.delete(id);
    $('#pessoasSelecionadas [data-pessoa-id="' + id + '"]').remove();
});

// Esconde resultados ao clicar fora
$(document).on('click', function(e) {
    if (!$(e.target).closest('#resultadosBusca, #buscaPessoa').length) {
        $('#resultadosBusca').hide();
    }
});

// Impede submit do form se o foco está no campo de busca
$('#formEndividamento').on('submit', function(event) {
    if (document.activeElement.id === 'buscaPessoa') {
        event.preventDefault();
        window.buscarPessoas();
        return false;
    }
    // ... resto da lógica de submit ...
});

// Função global para buscar pessoas (Enter ou botão)
window.buscarPessoas = function() {
    var termo = $('#buscaPessoa').val();
    var $resultados = $('#resultadosBusca');
    $resultados.empty().hide();
    if (termo.length < 2) {
        $resultados.append('<div class="list-group-item">Digite pelo menos 2 caracteres.</div>').show();
        return;
    }
    fetch(`/endividamentos/buscar-pessoas?q=${encodeURIComponent(termo)}`)
        .then(res => res.json())
        .then(function(pessoas) {
            $resultados.empty();
            if (pessoas.length === 0) {
                $resultados.append('<div class="list-group-item">Nenhuma pessoa encontrada.</div>').show();
            } else {
                pessoas.forEach(function(pessoa) {
                    $resultados.append(
                        `<div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${pessoa.nome}</strong><br>
                                <small class="text-muted">${pessoa.cpf_cnpj_formatado || pessoa.cpf_cnpj}</small>
                            </div>
                            <button type="button" class="btn btn-sm btn-primary selecionar-pessoa"
                                data-id="${pessoa.id}" data-nome="${pessoa.nome.replace(/'/g, "\\'")}" data-cpf-cnpj="${(pessoa.cpf_cnpj_formatado || pessoa.cpf_cnpj).replace(/'/g, "\\'")}">
                                Selecionar
                            </button>
                        </div>`
                    );
                });
                $resultados.show();
            }
        });
};