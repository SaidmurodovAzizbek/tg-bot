/**
 * Instagram Comment Analyzer — Frontend Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // ── Index sahifasi (Form yuborish) ─────────────────────────────────
    const analyzeForm = document.getElementById('analyze-form');
    
    if (analyzeForm) {
        const urlInput = document.getElementById('post-url');
        const submitBtn = document.getElementById('submit-btn');
        const loadingState = document.getElementById('loading-state');
        const errorState = document.getElementById('error-state');
        const errorText = document.getElementById('error-text');
        
        analyzeForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const url = urlInput.value.trim();
            if (!url) return;
            
            // UI ni loading holatiga o'tkazish
            analyzeForm.classList.add('hidden');
            errorState.classList.add('hidden');
            loadingState.classList.remove('hidden');
            
            // So'rov yuborish
            try {
                const formData = new FormData();
                formData.append('post_url', url);
                
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok && data.status === 'success') {
                    // Muvaffaqiyatli — natija sahifasiga yo'naltirish
                    window.location.href = `/result/${data.result_id}`;
                } else {
                    // Xatolik serverdan qaytdi
                    throw new Error(data.detail || "Noma'lum xatolik yuz berdi");
                }
                
            } catch (error) {
                // Xatolikni ko'rsatish va formani qaytarish
                loadingState.classList.add('hidden');
                analyzeForm.classList.remove('hidden');
                errorState.classList.remove('hidden');
                errorText.textContent = error.message;
            }
        });
    }
});

// ── Result sahifasi (Chart.js init) ────────────────────────────────
function initResultPage(sentimentData, categoriesData) {
    const ctx = document.getElementById('sentimentChart');
    if (!ctx) return;
    
    // CSS variable lardan ranglarni olish uchun map
    const colorMap = {
        'green': '#10b981',
        'red': '#ef4444',
        'blue': '#3b82f6',
        'yellow': '#f59e0b',
        'dim': '#64748b',
        'white': '#cbd5e1',
        'bright_magenta': '#d946ef'
    };

    // Chart.js global sozlamalari
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Inter', sans-serif";

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Ijobiy', 'Salbiy', 'Neytral'],
            datasets: [{
                data: [
                    sentimentData.positive, 
                    sentimentData.negative, 
                    sentimentData.neutral
                ],
                backgroundColor: [
                    colorMap['green'],
                    colorMap['red'],
                    colorMap['white']
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                legend: {
                    display: false // O'zimiz custom HTML legend yozdik
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleFont: { size: 14 },
                    bodyFont: { size: 14 },
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return ` ${context.label}: ${context.raw}%`;
                        }
                    }
                }
            },
            animation: {
                animateScale: true,
                animateRotate: true,
                duration: 1500,
                easing: 'easeOutQuart'
            }
        }
    });
}
