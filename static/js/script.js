// DDL Converter - JavaScript Functions
console.log('Script carregado com sucesso!');

let ddlFile = null;
let jsonFile = null;
let csvData = [];
let nomeTabela = '';

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const ddlInput = document.getElementById('ddlInput');
const jsonInput = document.getElementById('jsonInput');
const uploadSection = document.getElementById('uploadSection');
const csvEditorSection = document.getElementById('csvEditorSection');
const resultsSection = document.getElementById('resultsSection');
const loadingOverlay = document.getElementById('loadingOverlay');
const notification = document.getElementById('notification');

// File input listeners
ddlInput.addEventListener('change', function(e) {
    ddlFile = e.target.files[0];
    document.getElementById('ddlFileName').textContent = ddlFile ? '✓ ' + ddlFile.name : '';
});

jsonInput.addEventListener('change', function(e) {
    jsonFile = e.target.files[0];
    document.getElementById('jsonFileName').textContent = jsonFile ? '✓ ' + jsonFile.name : '';
});

// Função para comparar arquivos
function compareFiles() {
    if (!ddlFile || !jsonFile) {
        showNotification('Selecione ambos os arquivos (DDL e JSON)', 'warning');
        return;
    }
    
    showLoading();
    console.log('Iniciando comparação...');
    
    const formData = new FormData();
    formData.append('ddl_file', ddlFile);
    formData.append('json_file', jsonFile);
    
    fetch('/compare', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Response status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Response data:', data);
        hideLoading();
        
        if (data.success) {
            console.log('Sucesso! Dados recebidos:', data);
            csvData = data.dados_csv;
            nomeTabela = data.nome_tabela;
            
            displayCsvEditor(data);
            showNotification('Comparação realizada com sucesso!', 'success');
        } else {
            console.error('Erro na resposta:', data.error);
            showNotification(data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Erro na requisição:', error);
        hideLoading();
        showNotification('Erro na comparação: ' + error.message, 'error');
    });
}

// Função para exibir editor de CSV
function displayCsvEditor(data) {
    console.log('Exibindo editor de CSV...');
    console.log('csvEditorSection:', csvEditorSection);
    console.log('uploadSection:', uploadSection);
    
    uploadSection.style.display = 'none';
    csvEditorSection.style.display = 'block';
    
    console.log('Seções atualizadas');
    
    // Preencher estatísticas
    document.getElementById('tabelaNome').textContent = data.nome_tabela;
    document.getElementById('totalColunas').textContent = data.num_colunas;
    document.getElementById('colunasNovas').textContent = data.num_colunas_novas;
    document.getElementById('colunasExistentes').textContent = data.num_colunas_existentes;
    
    console.log('Estatísticas preenchidas');
    
    // Preencher tabela
    const tbody = document.getElementById('csvTableBody');
    tbody.innerHTML = '';
    
    console.log('Adicionando linhas:', data.dados_csv.length);
    
    for (let i = 0; i < data.dados_csv.length; i++) {
        const linha = data.dados_csv[i];
        const tr = document.createElement('tr');
        const isNova = !linha.rename_to;
        const isRemovida = linha.coluna_mf.includes('[REMOVIDA]');
        
        tr.innerHTML = `
            <td><strong>${linha.coluna_mf}</strong></td>
            <td><span style="color: #666;">${linha.tipo_original || 'VARCHAR'}</span></td>
            <td>
                <input type="text" class="csv-input" value="${linha.rename_to}" 
                       data-field="rename_to" data-row="${i}"
                       ${isRemovida ? 'disabled' : ''}
                       onchange="updateCsvData(this)">
            </td>
            <td>
                <input type="text" class="csv-input" value="${linha.descricao_oficial}" 
                       data-field="descricao_oficial" data-row="${i}"
                       ${isRemovida ? 'disabled' : ''}
                       onchange="updateCsvData(this)">
            </td>
            <td>
                <span class="status-badge ${isRemovida ? 'status-removed' : (isNova ? 'status-new' : 'status-existing')}">
                    ${isRemovida ? 'REMOVIDA' : (isNova ? 'NOVA' : 'EXISTENTE')}
                </span>
            </td>
        `;
        
        tbody.appendChild(tr);
    }
    
    console.log('Tabela preenchida com sucesso');
}

// Atualizar dados do CSV
function updateCsvData(input) {
    const rowIndex = parseInt(input.dataset.row);
    const field = input.dataset.field;
    csvData[rowIndex][field] = input.value;
}

// Salvar e gerar JSON
function salvarEGerar() {
    showLoading();
    
    fetch('/salvar_csv_json', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            dados_csv: csvData,
            nome_tabela: nomeTabela
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.success) {
            // Configura o botão de download para baixar o arquivo JSON
            document.getElementById('downloadJsonBtn').onclick = function() {
                downloadJson(data.json_filename);
            };
            
            csvEditorSection.style.display = 'none';
            resultsSection.style.display = 'block';
            showNotification('JSON gerado com sucesso!', 'success');
        } else {
            showNotification(data.error, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showNotification('Erro ao gerar JSON: ' + error.message, 'error');
    });
}

// Faz o download do arquivo JSON
function downloadJson(filename) {
    console.log(`[DEBUG] Iniciando download do arquivo: ${filename}`);
    
    // Criar um link temporário
    const link = document.createElement('a');
    link.href = `/download_json/${filename}`;
    
    // Forçar o download em vez de abrir em nova aba
    link.setAttribute('download', filename);
    
    // Adicionar o link ao documento
    document.body.appendChild(link);
    
    // Disparar o clique no link
    link.click();
    
    // Remover o link após o download
    setTimeout(() => {
        document.body.removeChild(link);
    }, 100);
    
    // Abrir em uma nova aba como fallback
    setTimeout(() => {
        window.open(`/download_json/${filename}`, '_blank');
    }, 200);
    
    console.log(`[DEBUG] Download do arquivo ${filename} solicitado`);
}

function startOver() {
    uploadSection.style.display = 'block';
    csvEditorSection.style.display = 'none';
    resultsSection.style.display = 'none';
    
    ddlFile = null;
    jsonFile = null;
    csvData = [];
    nomeTabela = '';
    
    document.getElementById('ddlFileName').textContent = '';
    document.getElementById('jsonFileName').textContent = '';
    document.getElementById('ddlInput').value = '';
    document.getElementById('jsonInput').value = '';
    
    showNotification('Pronto para processar novos arquivos', 'success');
}

function clearCache() {
    if (confirm('Tem certeza que deseja limpar o cache? Todos os arquivos processados serão removidos.')) {
        showLoading();
        
        fetch('/clear_cache', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                showNotification(data.message, 'success');
                startOver();
            } else {
                showNotification(data.error, 'error');
            }
        })
        .catch(error => {
            hideLoading();
            showNotification('Erro ao limpar cache: ' + error.message, 'error');
        });
    }
}

// Utility functions
function showLoading() {
    loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
}

function showNotification(message, type = 'success') {
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 5000);
}

// Tab Functions
function showTab(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    for (let tab of tabs) {
        tab.classList.remove('active');
    }
    
    // Remove active class from all buttons
    const buttons = document.querySelectorAll('.tab-btn');
    for (let btn of buttons) {
        btn.classList.remove('active');
    }
    
    // Show selected tab
    if (tabName === 'converter') {
        document.getElementById('converterTab').classList.add('active');
        document.querySelector('[onclick="showTab(\'converter\')"]').classList.add('active');
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    console.log('DDL Converter Web App initialized');
});
