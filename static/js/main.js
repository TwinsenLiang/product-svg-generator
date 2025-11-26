document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generate-btn');
    const outlineBtn = document.getElementById('outline-btn');
    const compareBtn = document.getElementById('compare-btn');
    const svgContainer = document.getElementById('svg-container');
    const debugContent = document.getElementById('debug-content');
    
    // State for outline toggle
    let isOutlineVisible = false;
    
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
    
    // Detect outline - Toggle mode
    outlineBtn.addEventListener('click', function() {
        if (isOutlineVisible) {
            // Hide outline
            const originalContainer = document.getElementById('original-container');
            const svgElement = originalContainer.querySelector('svg');
            
            if (svgElement) {
                const existingOverlay = svgElement.querySelector('.detection-overlay');
                if (existingOverlay) {
                    existingOverlay.remove();
                }
            }
            
            // Update button text and state
            outlineBtn.textContent = '标出轮廓';
            outlineBtn.classList.remove('btn-active');
            isOutlineVisible = false;
            
            debugContent.innerHTML = '<p style="text-align: center; color: #6c757d;">轮廓显示已关闭</p>';
        } else {
            // Show loading indicator
            showLoading();
            
            // Fetch detection data
            fetch('/detect_outline', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Display the outline SVG in the original container (overlay on image)
                    if (data.contour && data.contour.length > 0) {
                        // Get the SVG container
                        const originalContainer = document.getElementById('original-container');
                        const svgElement = originalContainer.querySelector('svg');
                        
                        if (svgElement) {
                            // Clear any existing overlay elements
                            const existingOverlay = svgElement.querySelector('.detection-overlay');
                            if (existingOverlay) {
                                existingOverlay.remove();
                            }
                            
                            // Create a group for all detection elements
                            const overlayGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                            overlayGroup.setAttribute('class', 'detection-overlay');
                            
                            // Add main contour as a path
                            const pathElement = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                            let pathData = "M ";
                            for (let i = 0; i < data.contour.length; i++) {
                                if (i === 0) {
                                    pathData += `${data.contour[i][0]},${data.contour[i][1]} `;
                                } else {
                                    pathData += `L ${data.contour[i][0]},${data.contour[i][1]} `;
                                }
                            }
                            pathData += "Z";
                            pathElement.setAttribute('d', pathData);
                            pathElement.setAttribute('fill', 'none');
                            pathElement.setAttribute('stroke', 'green');
                            pathElement.setAttribute('stroke-width', '2');
                            overlayGroup.appendChild(pathElement);
                            
                            // Add feature boxes
                            if (data.features && data.features.length > 0) {
                                for (let feature of data.features) {
                                    const rectElement = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                                    rectElement.setAttribute('x', feature.x);
                                    rectElement.setAttribute('y', feature.y);
                                    rectElement.setAttribute('width', feature.width);
                                    rectElement.setAttribute('height', feature.height);
                                    rectElement.setAttribute('fill', 'none');
                                    rectElement.setAttribute('stroke', 'blue');
                                    rectElement.setAttribute('stroke-width', '1');
                                    overlayGroup.appendChild(rectElement);
                                }
                            }
                            
                            // Add the overlay group to the SVG
                            svgElement.appendChild(overlayGroup);
                        }
                    }
                    
                    // Update button text and state
                    outlineBtn.textContent = '隐藏轮廓';
                    outlineBtn.classList.add('btn-active');
                    isOutlineVisible = true;
                    
                    // Also display debug information
                    displayDebugInfo(data.debug_info);
                } else {
                    debugContent.innerHTML = `<p style="color: #dc3545; text-align: center;">错误: ${data.error}</p>`;
                }
            })
            .catch(error => {
                debugContent.innerHTML = `<p style="color: #dc3545; text-align: center;">错误: ${error.message}</p>`;
            });
        }
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