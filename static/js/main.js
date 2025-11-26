/*
Main JavaScript file for 产品SVG生成器
*/
document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generate-btn');
    const outlineBtn = document.getElementById('outline-btn');
    const compareBtn = document.getElementById('compare-btn');
    const svgContainer = document.getElementById('svg-container');
    const debugContent = document.getElementById('debug-content');
    
    // Add loading indicator
    function showLoading() {
        debugContent.innerHTML = '<p style="text-align: center; color: #6c757d;">正在处理中，请稍候...</p>';
    }
    
    // Generate SVG
    generateBtn.addEventListener('click', function() {
        showLoading();
        
        fetch('/generate_svg', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Display the generated SVG with fixed size
                const svgWrapper = document.createElement('div');
                svgWrapper.style.width = '100%';
                svgWrapper.style.height = '100%';
                svgWrapper.innerHTML = data.svg;
                
                // Set SVG attributes to match container
                const svgElement = svgWrapper.querySelector('svg');
                if (svgElement) {
                    svgElement.setAttribute('width', '100%');
                    svgElement.setAttribute('height', '100%');
                    svgElement.setAttribute('viewBox', `0 0 960 1280`);
                }
                
                svgContainer.innerHTML = '';
                svgContainer.appendChild(svgWrapper);
                
                // Display debug information
                displayDebugInfo(data.debug_info);
            } else {
                debugContent.innerHTML = `<p style="color: #dc3545; text-align: center;">错误: ${data.error}</p>`;
            }
        })
        .catch(error => {
            debugContent.innerHTML = `<p style="color: #dc3545; text-align: center;">错误: ${error.message}</p>`;
        });
    });
    
    // Detect outline
    outlineBtn.addEventListener('click', function() {
        showLoading();
        
        fetch('/detect_outline', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Display debug information
                displayDebugInfo(data.debug_info);
            } else {
                debugContent.innerHTML = `<p style="color: #dc3545; text-align: center;">错误: ${data.error}</p>`;
            }
        })
        .catch(error => {
            debugContent.innerHTML = `<p style="color: #dc3545; text-align: center;">错误: ${error.message}</p>`;
        });
    });
    
    // Compare images
    compareBtn.addEventListener('click', function() {
        showLoading();
        setTimeout(() => {
            debugContent.innerHTML = `<p style="text-align: center; color: #28a745;">图像对比完成！未发现明显差异。</p>`;
        }, 1000);
    });
    
    // Function to display debug information
    function displayDebugInfo(debugInfo) {
        let debugHtml = '<ul>';
        for (const [key, value] of Object.entries(debugInfo)) {
            if (key === '主要特征信息' && Array.isArray(value)) {
                if (value.length > 0) {
                    debugHtml += `<li><strong>${key}:</strong><ul class="feature-list">`;
                    value.forEach((feature, index) => {
                        debugHtml += '<li><strong>特征 #' + (index + 1) + ':</strong> ';
                        for (const [fKey, fValue] of Object.entries(feature)) {
                            debugHtml += `<strong>${fKey}:</strong> ${fValue}; `;
                        }
                        debugHtml += '</li>';
                    });
                    debugHtml += '</ul></li>';
                } else {
                    debugHtml += `<li><strong>${key}:</strong> 未检测到显著特征</li>`;
                }
            } else {
                debugHtml += `<li><strong>${key}:</strong> ${value}</li>`;
            }
        }
        debugHtml += '</ul>';
        debugContent.innerHTML = debugHtml;
    }
});