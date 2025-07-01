// src/static/js/auditoria.js

document.addEventListener('DOMContentLoaded', function () {
  function carregarTabela(url) {
    fetch(url, {
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
      .then(response => {
        if (!response.ok) throw new Error('Erro ao carregar tabela');
        return response.text();
      })
      .then(html => {
        document.getElementById('auditoria-table').innerHTML = html;
        // Não precisa reativar paginacao, pois usamos delegation agora!
      })
      .catch(error => {
        alert('Falha ao atualizar tabela: ' + error.message);
      });
  }

  // Delegação de evento para melhor performance e evitar múltiplos bindings após update
  document.getElementById('auditoria-table').addEventListener('click', function (e) {
    if (e.target.matches('.pagination a.page-link')) {
      e.preventDefault();
      const url = e.target.getAttribute('href');
      if (url) {
        carregarTabela(url);
      }
    }
  });
});