// DDL Converter - JavaScript Functions

let uploadedFiles = [];
let currentThreadId = null;
let sessionHistory = [];

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const fileItems = document.getElementById('fileItems');
const processBtn = document.getElementById('processBtn');
const uploadSection = document.getElementById('uploadSection');
const processSection = document.getElementById('processSection');
const resultsSection = document.getElementById('resultsSection');
const loadingOverlay = document.getElementById('loadingOverlay');
const notification = document.getElementById('notification');

// Initialize drag and drop
uploadArea.addEventListener('dragover', handleDragOver);
uploadArea.addEventListener('dragleave', handleDragLeave);
uploadArea.addEventListener('drop', handleDrop);
uploadArea.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', handleFileSelect);

function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    handleFiles(files);
}

function handleFiles(files) {
    if (files.length === 0) return;
    
    showLoading();
    
    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.success) {
            uploadedFiles = data.uploaded_files;
            displayFiles(data.uploaded_files, data.skipped_files);
            
            let message = data.message;
            if (data.skipped_files.length > 0) {
                message += `. ${data.skipped_files.length} arquivo(s) ignorado(s) (já processados anteriormente)`;
            }
            showNotification(message, 'success');
        } else {
            showNotification(data.error, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showNotification('Erro ao enviar arquivos: ' + error.message, 'error');
    });
}

function displayFiles(files, skippedFiles = []) {
    fileItems.innerHTML = '';
    
    // Mostrar arquivos enviados
    files.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info-item">
                <i class="fas fa-file-alt"></i>
                <span>${file.filename}</span>
            </div>
            <span class="file-status status-new">Novo</span>
        `;
        fileItems.appendChild(fileItem);
    });
    
    // Mostrar arquivos ignorados
    skippedFiles.forEach(filename => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info-item">
                <i class="fas fa-file-alt"></i>
                <span>${filename}</span>
            </div>
            <span class="file-status status-duplicate">Já processado</span>
        `;
        fileItems.appendChild(fileItem);
    });
    
    if (files.length > 0) {
        fileList.style.display = 'block';
        processBtn.disabled = false;
    } else {
        fileList.style.display = 'none';
    }
}

function clearFiles() {
    uploadedFiles = [];
    fileList.style.display = 'none';
    fileInput.value = '';
    showNotification('Lista de arquivos limpa', 'success');
}

function processFiles() {
    if (uploadedFiles.length === 0) {
        showNotification('Nenhum arquivo para processar', 'warning');
        return;
    }
    
    showLoading();
    
    fetch('/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            files: uploadedFiles
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.success) {
            currentThreadId = data.thread_id;
            showProcessingSection();
            monitorProgress();
            showNotification('Processamento iniciado', 'success');
        } else {
            showNotification(data.error, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showNotification('Erro ao iniciar processamento: ' + error.message, 'error');
    });
}

function showProcessingSection() {
    uploadSection.style.display = 'none';
    processSection.style.display = 'block';
    resultsSection.style.display = 'none';
}

function monitorProgress() {
    if (!currentThreadId) return;
    
    const checkStatus = () => {
        fetch(`/status/${currentThreadId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const status = data.status;
                updateProgress(status);
                
                if (status.status === 'completed') {
                    showResults(status);
                } else {
                    setTimeout(checkStatus, 1000); // Check again in 1 second
                }
            } else {
                showNotification('Erro ao verificar status', 'error');
            }
        })
        .catch(error => {
            showNotification('Erro de conexão: ' + error.message, 'error');
        });
    };
    
    checkStatus();
}

function updateProgress(status) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const processStatus = document.getElementById('processStatus');
    
    const percentage = Math.round((status.completed / status.total) * 100);
    
    progressFill.style.width = percentage + '%';
    progressText.textContent = percentage + '%';
    processStatus.textContent = `Processando arquivo ${status.completed} de ${status.total}...`;
}

function showResults(status) {
    processSection.style.display = 'none';
    resultsSection.style.display = 'block';
    
    displayResults(status.results, status.errors);
    
    if (status.results.length > 0) {
        showNotification(`${status.results.length} arquivo(s) processado(s) com sucesso!`, 'success');
        // Atualizar histórico da sessão
        refreshHistory();
    }
    
    if (status.errors.length > 0) {
        showNotification(`${status.errors.length} arquivo(s) com erro`, 'error');
    }
}

function displayResults(results, errors) {
    const successResults = document.getElementById('successResults');
    const errorResults = document.getElementById('errorResults');
    
    // Clear previous results
    successResults.innerHTML = '';
    errorResults.innerHTML = '';
    
    // Display successful results
    results.forEach(result => {
        const resultCard = document.createElement('div');
        resultCard.className = 'result-card';
        resultCard.innerHTML = `
            <h4><i class="fas fa-check-circle"></i> ${result.filename}</h4>
            <div class="result-info">
                <p><strong>Tabela:</strong> ${result.table_name}</p>
                <p><strong>Colunas:</strong> ${result.columns}</p>
            </div>
            <div class="result-downloads">
                <a href="/download/${result.csv_path.replace(/\\/g, '/')}" class="download-btn">
                    <i class="fas fa-file-csv"></i> CSV
                </a>
                <a href="/download/${result.json_path.replace(/\\/g, '/')}" class="download-btn">
                    <i class="fas fa-file-code"></i> JSON
                </a>
            </div>
        `;
        successResults.appendChild(resultCard);
    });
    
    // Display errors if any
    if (errors.length > 0) {
        errorResults.style.display = 'block';
        errorResults.innerHTML = `
            <h4><i class="fas fa-exclamation-triangle"></i> Arquivos com Erro</h4>
        `;
        
        errors.forEach(error => {
            const errorItem = document.createElement('div');
            errorItem.className = 'error-item';
            errorItem.innerHTML = `
                <strong>${error.filename}:</strong> ${error.error}
            `;
            errorResults.appendChild(errorItem);
        });
    }
}

function downloadAll() {
    window.location.href = '/download_all';
}

function startOver() {
    uploadSection.style.display = 'block';
    processSection.style.display = 'none';
    resultsSection.style.display = 'none';
    
    clearFiles();
    currentThreadId = null;
    
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
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    if (tabName === 'converter') {
        document.getElementById('converterTab').classList.add('active');
        document.querySelector('[onclick="showTab(\'converter\')"]').classList.add('active');
    } else if (tabName === 'history') {
        document.getElementById('historyTab').classList.add('active');
        document.querySelector('[onclick="showTab(\'history\')"]').classList.add('active');
        refreshHistory();
    }
}

// History Functions
function refreshHistory() {
    fetch('/session_history')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            sessionHistory = data.history;
            displayHistory(sessionHistory);
            updateHistoryCount();
        }
    })
    .catch(error => {
        console.error('Erro ao carregar histórico:', error);
    });
}

function displayHistory(history) {
    const historyContent = document.getElementById('historyContent');
    
    if (history.length === 0) {
        historyContent.innerHTML = `
            <div class="empty-history">
                <i class="fas fa-clock"></i>
                <h3>Nenhum arquivo processado ainda</h3>
                <p>Os arquivos convertidos nesta sessão aparecerão aqui</p>
            </div>
        `;
        return;
    }
    
    const historyGrid = document.createElement('div');
    historyGrid.className = 'history-grid';
    
    history.forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.innerHTML = `
            <div class="history-item-header">
                <div>
                    <div class="history-item-title">${item.filename}</div>
                </div>
                <div class="history-item-time">
                    ${item.date}<br>
                    ${item.timestamp}
                </div>
            </div>
            <div class="history-item-info">
                <p><strong>Tabela:</strong> ${item.table_name}</p>
                <p><strong>Colunas:</strong> ${item.columns}</p>
            </div>
            <div class="history-item-downloads">
                <a href="/download/${item.csv_path.replace(/\\/g, '/')}" class="download-btn">
                    <i class="fas fa-file-csv"></i> CSV
                </a>
                <a href="/download/${item.json_path.replace(/\\/g, '/')}" class="download-btn">
                    <i class="fas fa-file-code"></i> JSON
                </a>
            </div>
        `;
        historyGrid.appendChild(historyItem);
    });
    
    historyContent.innerHTML = '';
    historyContent.appendChild(historyGrid);
}

function updateHistoryCount() {
    const historyCount = document.getElementById('historyCount');
    historyCount.textContent = sessionHistory.length;
}

function clearSessionHistory() {
    if (confirm('Tem certeza que deseja limpar o histórico da sessão? Os arquivos não serão removidos.')) {
        sessionHistory = [];
        displayHistory([]);
        updateHistoryCount();
        showNotification('Histórico da sessão limpo', 'success');
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    console.log('DDL Converter Web App initialized');
    refreshHistory(); // Carregar histórico inicial
});
