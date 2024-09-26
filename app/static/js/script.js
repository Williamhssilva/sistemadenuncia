let categoriasChart, statusChart, denunciasChart;
let currentFilter = 1; // Alterado para 1 (hoje) como padrão

document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('denunciaModal');
    const closeButton = document.querySelector('.close');
    const statusSelect = document.getElementById('modalStatus');
    const atualizarStatusBtn = document.getElementById('atualizarStatus');
    const form = document.getElementById('denunciaForm');
    const mensagem = document.getElementById('mensagem');
    let denunciaAtualId;
    let categoriasChart, statusChart, denunciasChart;
    let currentFilter = 1; // Alterado para 1 (hoje) como padrão

    function atualizarDashboard() {
        const tbody = document.querySelector('table tbody');
        const categoriasCanvas = document.getElementById('categoriasChart');
        const statusCanvas = document.getElementById('statusChart');
        const denunciasCanvas = document.getElementById('denunciasChart');
        
        if (!tbody && !categoriasCanvas && !statusCanvas && !denunciasCanvas) return;

        fetch('/get_dashboard_data')
            .then(response => response.json())
            .then(data => {
                if (tbody) {
                    tbody.innerHTML = ''; // Limpa a tabela atual
                    data.denuncias.forEach(denuncia => {
                        const row = document.createElement('tr');
                        row.className = 'denuncia-row';
                        row.setAttribute('data-id', denuncia.id);
                        row.innerHTML = `
                            <td>${denuncia.id}</td>
                            <td>${denuncia.categoria}</td>
                            <td>${denuncia.local || 'N/A'}</td>
                            <td>${denuncia.data_ocorrencia || 'N/A'}</td>
                            <td class="conteudo-col">${denuncia.conteudo}</td>
                            <td>${denuncia.status}</td>
                            <td>${denuncia.data_criacao}</td>
                        `;
                        tbody.appendChild(row);
                    });
                    adicionarEventListenersLinhas();
                }

                if (categoriasCanvas) {
                    categoriasChart = atualizarGrafico(categoriasChart, categoriasCanvas, data.categorias, 'Categorias');
                }

                if (statusCanvas) {
                    statusChart = atualizarGrafico(statusChart, statusCanvas, data.status, 'Status');
                }

                if (denunciasCanvas) {
                    denunciasChart = atualizarGraficoDenuncias(denunciasChart, denunciasCanvas, data.denuncias_por_dia, currentFilter);
                }

                const totalDenuncias = document.getElementById('totalDenuncias');
                if (totalDenuncias) {
                    totalDenuncias.textContent = data.total_denuncias;
                }
            });
    }

    function adicionarEventListenersLinhas() {
        document.querySelectorAll('.denuncia-row').forEach(row => {
            row.addEventListener('click', abrirModal);
        });
    }

    function abrirModal() {
        denunciaAtualId = this.getAttribute('data-id');
        fetch(`/denuncia/${denunciaAtualId}`)
            .then(response => response.json())
            .then(data => {
                document.getElementById('modalId').textContent = data.id;
                document.getElementById('modalCategoria').textContent = data.categoria;
                document.getElementById('modalLocal').textContent = data.local || 'N/A';
                document.getElementById('modalDataOcorrencia').textContent = data.data_ocorrencia || 'N/A';
                document.getElementById('modalConteudo').textContent = data.conteudo;
                if (statusSelect) statusSelect.value = data.status;
                document.getElementById('modalDataCriacao').textContent = data.data_criacao;
                if (modal) modal.style.display = 'block';
            });
    }

    if (atualizarStatusBtn && statusSelect) {
        atualizarStatusBtn.addEventListener('click', function() {
            const novoStatus = statusSelect.value;
            fetch(`/atualizar_status/${denunciaAtualId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status: novoStatus }),
            })
            .then(response => response.json())
            .then(data => {
                
                atualizarDashboard();
                if (modal) modal.style.display = 'none';
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Erro ao atualizar o status.');
            });
        });
    }

    if (closeButton && modal) {
        closeButton.onclick = function() {
            modal.style.display = 'none';
        }

        window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
    }

    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const categoria = document.getElementById('categoria').value;
            const local = document.getElementById('local').value;
            const dataOcorrencia = document.getElementById('dataOcorrencia').value;
            const conteudo = document.getElementById('conteudoDenuncia').value;

            fetch('/denunciar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    categoria: categoria,
                    local: local,
                    data_ocorrencia: dataOcorrencia,
                    conteudo: conteudo 
                }),
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw err; });
                }
                return response.json();
            })
            .then(data => {
                if (mensagem) {
                    mensagem.textContent = 'Denúncia enviada com sucesso!';
                    mensagem.style.color = 'var(--primary-color)';
                }
                form.reset();
                // Não chama atualizarTabelaDenuncias() aqui, pois estamos na página de envio
            })
            .catch((error) => {
                console.error('Erro:', error);
                if (mensagem) {
                    mensagem.textContent = `Erro ao enviar a denúncia: ${error.error || 'Erro desconhecido'}`;
                    mensagem.style.color = 'var(--accent-color)';
                }
            });
        });
    }

    function atualizarGrafico(chart, canvas, dados, titulo) {
        const ctx = canvas.getContext('2d');
        const labels = Object.keys(dados);
        const values = Object.values(dados);

        if (chart) {
            chart.destroy(); // Destruir o gráfico existente
        }

        chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    title: {
                        display: true,
                        text: titulo
                    }
                }
            }
        });

        return chart;
    }

    function atualizarGraficoDenuncias(chart, canvas, dados, dias) {
        const ctx = canvas.getContext('2d');
        const labels = Object.keys(dados).slice(-dias);
        const values = Object.values(dados).slice(-dias);

        if (chart) {
            chart.destroy(); // Destruir o gráfico existente
        }

        chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Denúncias por dia',
                    data: values,
                    backgroundColor: 'rgba(57, 255, 20, 0.5)',
                    borderColor: 'rgba(57, 255, 20, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: dias === 1 ? 'Denúncias de Hoje' : `Denúncias dos Últimos ${dias} Dias`
                    }
                }
            }
        });

        return chart;
    }

    // Inicializa os event listeners das linhas e atualização periódica apenas se a tabela ou o card de status existir
    const tbody = document.querySelector('table tbody');
    const categoriasCanvas = document.getElementById('categoriasChart');
    const statusCanvas = document.getElementById('statusChart');
    const denunciasCanvas = document.getElementById('denunciasChart');
    if (tbody || categoriasCanvas || statusCanvas || denunciasCanvas) {
        atualizarDashboard();
        setInterval(atualizarDashboard, 30000);
    }

    const filterButtons = document.querySelectorAll('.filter-buttons button');
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            currentFilter = parseInt(this.dataset.filter);
            atualizarDashboard();
        });
    });
});