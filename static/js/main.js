document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generate-btn');
    const outlineBtn = document.getElementById('outline-btn');
    const compareBtn = document.getElementById('compare-btn');
    const exportSvgBtn = document.getElementById('export-svg-btn');
    const svgContainer = document.getElementById('svg-container');
    const debugContent = document.getElementById('debug-content');

    // 调试：检查按钮是否存在
    console.log('[初始化] exportSvgBtn:', exportSvgBtn);

    // State for outline toggle
    let isOutlineVisible = false;

    // 存储生成的SVG内容
    let generatedSvgContent = null;
    
    // Add loading indicator
    function showLoading() {
        debugContent.innerHTML = '<p style="text-align: center; color: #6c757d;">正在处理中，请稍候...</p>';
    }
    
    // 更换图片按钮
    const changeImageBtn = document.getElementById('change-image-btn');
    const changeImageUpload = document.getElementById('change-image-upload');

    if (changeImageBtn && changeImageUpload) {
        changeImageBtn.addEventListener('click', function() {
            console.log('点击更换图片按钮');
            changeImageUpload.click();
        });

        changeImageUpload.addEventListener('change', function() {
            console.log('选择新图片:', this.files);
            if (this.files.length > 0) {
                uploadProductImage(this.files[0]);
            }
        });
    }

    // 加载产品图片预览
    loadCroppedPreview();

    // 设置产品图片上传
    function setupProductImageUpload() {
        const productUploadArea = document.getElementById('product-upload-area');
        const productImageUpload = document.getElementById('product-image-upload');

        if (!productUploadArea || !productImageUpload) {
            console.log('上传区域或输入框未找到');
            return;
        }

        console.log('设置上传区域事件监听');

        // 点击上传区域
        productUploadArea.addEventListener('click', function(e) {
            console.log('点击上传区域');
            e.stopPropagation();
            productImageUpload.click();
        });

        // 文件选择
        productImageUpload.addEventListener('change', function() {
            console.log('文件已选择:', this.files);
            if (this.files.length > 0) {
                uploadProductImage(this.files[0]);
            }
        });

        // 拖拽上传
        productUploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('拖拽悬停');
            productUploadArea.classList.add('drag-over');
        });

        productUploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('拖拽离开');
            productUploadArea.classList.remove('drag-over');
        });

        productUploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('文件拖放:', e.dataTransfer.files);
            productUploadArea.classList.remove('drag-over');

            if (e.dataTransfer.files.length > 0) {
                uploadProductImage(e.dataTransfer.files[0]);
            }
        });
    }

    // 上传产品图片
    function uploadProductImage(file) {
        console.log('开始上传文件:', file.name);

        const formData = new FormData();
        formData.append('image', file);

        // 显示上传中状态
        const originalContainer = document.getElementById('original-container');
        if (originalContainer) {
            originalContainer.innerHTML = '<div style="display: flex; justify-content: center; align-items: center; height: 100%;"><p>正在上传...</p></div>';
        }
        debugContent.innerHTML = '<p style="text-align: center; color: #6c757d;">正在上传产品图片...</p>';

        fetch('/upload_product_image', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('上传响应状态:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('上传响应数据:', data);
            if (data.success) {
                // 上传成功，显示提示并加载图片
                debugContent.innerHTML = `<p style="color: #28a745; text-align: center;">${data.message}</p>`;
                // 重新加载产品图片
                loadCroppedPreview();
            } else {
                // 上传失败，恢复上传区域
                console.error('上传失败:', data.error);
                showUploadArea();
                debugContent.innerHTML = `<p style="color: #dc3545; text-align: center;">上传失败: ${data.error}</p>`;
            }
        })
        .catch(error => {
            // 错误处理，恢复上传区域
            console.error('上传错误:', error);
            showUploadArea();
            debugContent.innerHTML = `<p style="color: #dc3545; text-align: center;">上传错误: ${error.message}</p>`;
        });
    }

    // 显示上传区域
    function showUploadArea() {
        const originalContainer = document.getElementById('original-container');
        if (originalContainer) {
            originalContainer.innerHTML = `
                <div class="product-upload-area" id="product-upload-area">
                    <div class="upload-icon">📷</div>
                    <p>点击或拖拽上传产品图片</p>
                    <p class="upload-hint">支持 JPG、PNG 格式</p>
                    <input type="file" id="product-image-upload" accept="image/jpeg,image/png,image/jpg" style="display: none;">
                </div>
            `;
            setupProductImageUpload();
        }
    }

    // Function to load and display cropped preview
    function loadCroppedPreview() {
        // Show loading indicator
        const originalContainer = document.getElementById('original-container');
        if (originalContainer) {
            originalContainer.innerHTML = '<div style="display: flex; justify-content: center; align-items: center; height: 100%;"><p>正在加载产品原图...</p></div>';
        }
        
        fetch('/get_cropped_image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const originalContainer = document.getElementById('original-container');
                if (originalContainer) {
                    // Create SVG container for the cropped image
                    originalContainer.innerHTML = `
                        <svg width="100%" height="100%" viewBox="0 0 ${data.crop_info.width} ${data.crop_info.height}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
                            <image href="${data.image_data}" width="${data.crop_info.width}" height="${data.crop_info.height}" />
                            <!-- Detection contours will be overlaid here -->
                        </svg>
                    `;
                }
            } else {
                // 加载失败，显示上传区域
                console.error('Server error:', data.error);
                showUploadArea();
            }
        })
        .catch(error => {
            // 网络错误，显示上传区域
            console.error('Error loading cropped preview:', error);
            showUploadArea();
        });
    }
    
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
                // 保存SVG内容供导出使用
                generatedSvgContent = data.svg;

                // Display the generated SVG with fixed size
                const svgWrapper = document.createElement('div');
                svgWrapper.style.width = '100%';
                svgWrapper.style.height = '100%';
                svgWrapper.style.display = 'flex';
                svgWrapper.style.alignItems = 'center';
                svgWrapper.style.justifyContent = 'center';
                svgWrapper.innerHTML = data.svg;

                // Set SVG attributes to match container
                const svgElement = svgWrapper.querySelector('svg');
                if (svgElement) {
                    // 保留SVG原始的viewBox，不要强制覆盖
                    const originalViewBox = svgElement.getAttribute('viewBox');
                    console.log('[SVG显示] 原始viewBox:', originalViewBox);

                    svgElement.setAttribute('width', '100%');
                    svgElement.setAttribute('height', '100%');
                    svgElement.setAttribute('preserveAspectRatio', 'xMidYMid meet');
                    // 不覆盖viewBox，使用SVG自带的viewBox
                }

                svgContainer.innerHTML = '';
                svgContainer.appendChild(svgWrapper);

                // 显示导出按钮（添加安全检查）
                if (exportSvgBtn) {
                    console.log('[SVG生成成功] 显示导出按钮');
                    exportSvgBtn.style.display = 'inline-block';
                } else {
                    console.error('[SVG生成成功] 导出按钮不存在！');
                }

                // Display debug information
                displayDebugInfo(data.debug_info);
            } else {
                debugContent.innerHTML = `<p style="color: #dc3545; text-align: center;">错误: ${data.error}</p>`;
                // 隐藏导出按钮（添加安全检查）
                if (exportSvgBtn) {
                    exportSvgBtn.style.display = 'none';
                }
            }
        })
        .catch(error => {
            debugContent.innerHTML = `<p style="color: #dc3545; text-align: center;">错误: ${error.message}</p>`;
        });
    });

    // 导出SVG功能
    if (exportSvgBtn) {
        exportSvgBtn.addEventListener('click', function() {
            if (!generatedSvgContent) {
                alert('请先生成SVG');
                return;
            }

            // 创建Blob对象
            const blob = new Blob([generatedSvgContent], { type: 'image/svg+xml' });
            const url = URL.createObjectURL(blob);

            // 创建下载链接
            const link = document.createElement('a');
            link.href = url;
            const timestamp = new Date().getTime();
            link.download = `product_${timestamp}.svg`;

            // 触发下载
            document.body.appendChild(link);
            link.click();

            // 清理
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            console.log('SVG已导出');
        });
    }

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
                    // Display all contours with color-coded boxes
                    if (data.contours && data.contours.length > 0) {
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

                            // Color mapping for different contour types
                            const colorMap = {
                                'body': '#ff0000',           // 红色 - 主体
                                'circle_control': '#ffff00', // 黄色 - 圆形控制区
                                'button': '#0000ff',         // 蓝色 - 按钮
                                'unknown': '#ffffff'         // 白色 - 未知
                            };

                            // Draw all contours as rectangles
                            for (let contour of data.contours) {
                                const rectElement = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                                rectElement.setAttribute('x', contour.x);
                                rectElement.setAttribute('y', contour.y);
                                rectElement.setAttribute('width', contour.width);
                                rectElement.setAttribute('height', contour.height);
                                rectElement.setAttribute('fill', 'none');
                                rectElement.setAttribute('stroke', colorMap[contour.type] || '#cccccc');
                                rectElement.setAttribute('stroke-width', '2');
                                overlayGroup.appendChild(rectElement);

                                // Add label for contour type
                                const textElement = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                                textElement.setAttribute('x', contour.x + 5);
                                textElement.setAttribute('y', contour.y + 15);
                                textElement.setAttribute('fill', colorMap[contour.type] || '#cccccc');
                                textElement.setAttribute('font-size', '12');
                                textElement.setAttribute('font-weight', 'bold');
                                textElement.textContent = contour.type;
                                overlayGroup.appendChild(textElement);
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
    
    // Compare images - removed duplicate listener (see line 527 for actual implementation)
    
    // ==================== 标记校验功能 ====================
    let markerPairs = [];
    let nextMarkerId = 1;

    // 从图像提取颜色
    function extractColorFromImage(imageElement, x, y) {
        try {
            // 创建canvas来读取像素
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d', { willReadFrequently: true });

            // 设置canvas尺寸为图像尺寸
            canvas.width = imageElement.naturalWidth || imageElement.width;
            canvas.height = imageElement.naturalHeight || imageElement.height;

            // 绘制图像
            ctx.drawImage(imageElement, 0, 0);

            // 读取指定位置的像素数据
            const pixel = ctx.getImageData(x, y, 1, 1).data;

            const r = pixel[0];
            const g = pixel[1];
            const b = pixel[2];
            const hex = ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');

            console.log(`[取色] 坐标(${x.toFixed(0)}, ${y.toFixed(0)}) -> RGB(${r}, ${g}, ${b}) #${hex}`);

            return { r, g, b, hex };
        } catch (e) {
            console.error('[取色] 提取颜色失败:', e);
            return null;
        }
    }

    // 获取鼠标相对于元素的位置（返回DOM坐标和SVG坐标）
    function getMousePosition(element, event) {
        const rect = element.getBoundingClientRect();
        const domX = event.clientX - rect.left;
        const domY = event.clientY - rect.top;

        // 获取容器内的SVG元素
        const svg = element.querySelector('svg');
        if (!svg) {
            return { domX, domY, svgX: domX, svgY: domY };
        }

        // 获取SVG的viewBox
        const viewBox = svg.viewBox.baseVal;
        if (!viewBox || viewBox.width === 0) {
            return { domX, domY, svgX: domX, svgY: domY };
        }

        // 获取SVG的实际显示尺寸（考虑padding）
        const svgRect = svg.getBoundingClientRect();

        // 计算点击位置相对于SVG元素的坐标
        const clickOnSvgX = event.clientX - svgRect.left;
        const clickOnSvgY = event.clientY - svgRect.top;

        // 转换到viewBox坐标系
        const scaleX = viewBox.width / svgRect.width;
        const scaleY = viewBox.height / svgRect.height;

        const svgX = clickOnSvgX * scaleX + viewBox.x;
        const svgY = clickOnSvgY * scaleY + viewBox.y;

        console.log(`[坐标转换] DOM(${domX.toFixed(1)}, ${domY.toFixed(1)}) -> SVG viewBox(${svgX.toFixed(1)}, ${svgY.toFixed(1)})`);

        return { domX, domY, svgX, svgY };
    }

    // 在容器中添加标记（使用DOM坐标）
    function addMarkerToContainer(container, domX, domY, type, id) {
        const marker = document.createElement('div');
        marker.className = `marker marker-${type}`;
        marker.style.left = `${domX - 12}px`;  // 居中标记（24px/2）
        marker.style.top = `${domY - 12}px`;
        marker.textContent = id;
        marker.setAttribute('data-id', id);
        marker.setAttribute('data-type', type);

        container.appendChild(marker);
        console.log(`添加标记 #${id} 到 ${type}，DOM位置: (${domX.toFixed(1)}, ${domY.toFixed(1)})`);
    }

    // 统一的点击事件处理（使用事件委托）
    document.addEventListener('click', function(event) {
        // 检查标记模式是否激活
        if (!compareBtn.classList.contains('btn-active')) return;

        // 检查是否点击在已有标记上（忽略）
        if (event.target.classList.contains('marker')) {
            console.log('点击了标记，忽略');
            return;
        }

        const originalContainer = document.getElementById('original-container');
        const svgContainer = document.getElementById('svg-container');

        // 检查点击是否在原图容器内
        if (originalContainer && originalContainer.contains(event.target)) {
            console.log('✓ 原图容器被点击');
            const pos = getMousePosition(originalContainer, event);

            // 保存当前的markerId（避免异步回调时ID已变化）
            const currentMarkerId = nextMarkerId;

            // 添加标记到原图（使用DOM坐标显示）
            addMarkerToContainer(originalContainer, pos.domX, pos.domY, 'original', currentMarkerId);

            // 存储标记数据（使用SVG坐标，颜色稍后异步更新）
            markerPairs.push({
                id: currentMarkerId,
                original: { x: pos.svgX, y: pos.svgY, color: null },
                svg: null
            });

            console.log(`📍 标记 #${currentMarkerId} - 原图已标记，SVG坐标: (${pos.svgX.toFixed(1)}, ${pos.svgY.toFixed(1)})`);

            // 提取颜色（使用SVG坐标）
            const imageElement = originalContainer.querySelector('image');
            if (imageElement) {
                // 创建临时img元素来提取颜色
                const img = new Image();
                img.crossOrigin = 'anonymous';
                img.src = imageElement.getAttribute('href');
                img.onload = function() {
                    const color = extractColorFromImage(img, Math.floor(pos.svgX), Math.floor(pos.svgY));

                    // 更新markerPairs中的颜色数据
                    const pair = markerPairs.find(p => p.id === currentMarkerId);
                    if (pair && pair.original) {
                        pair.original.color = color;
                        console.log(`[颜色已更新] 标记 #${currentMarkerId}`, color);
                        updateMarkerDebugInfo();
                    }
                };
            }

            nextMarkerId++;
            updateMarkerDebugInfo();
            return;
        }

        // 检查点击是否在SVG容器内
        if (svgContainer && svgContainer.contains(event.target)) {
            console.log('✓ SVG容器被点击');
            const pos = getMousePosition(svgContainer, event);

            // 查找还没有SVG位置的最早标记
            let pair = markerPairs.find(p => p.original !== null && p.svg === null);

            if (pair) {
                // 更新现有标记对（使用SVG坐标存储数据）
                pair.svg = { x: pos.svgX, y: pos.svgY };
                // 使用DOM坐标显示标记
                addMarkerToContainer(svgContainer, pos.domX, pos.domY, 'svg', pair.id);
                console.log(`📍 标记 #${pair.id} - SVG已标记，配对完成，SVG坐标: (${pos.svgX.toFixed(1)}, ${pos.svgY.toFixed(1)})`);
            } else {
                // 创建新的仅有SVG位置的标记
                addMarkerToContainer(svgContainer, pos.domX, pos.domY, 'svg', nextMarkerId);
                markerPairs.push({
                    id: nextMarkerId,
                    original: null,
                    svg: { x: pos.svgX, y: pos.svgY }
                });
                console.log(`📍 标记 #${nextMarkerId} - 仅SVG标记，SVG坐标: (${pos.svgX.toFixed(1)}, ${pos.svgY.toFixed(1)})`);
                nextMarkerId++;
            }

            updateMarkerDebugInfo();
            return;
        }
    });

    // 更新调试信息
    function updateMarkerDebugInfo() {
        let debugHtml = '<h3>📍 标记校验结果</h3>';

        if (markerPairs.length === 0) {
            debugHtml += '<p style="color: #6c757d; text-align: center;">尚未添加标记。请在左侧原图和右侧SVG上点击对应位置进行标记。</p>';
            debugContent.innerHTML = debugHtml;
            return;
        }

        debugHtml += '<div style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px;">';
        debugHtml += '<strong>使用说明：</strong><br>';
        debugHtml += '🔴 红色数字 = 原图标记 &nbsp;&nbsp; 🔵 蓝色数字 = SVG标记<br>';
        debugHtml += '先在原图点击，再在SVG对应位置点击，即可完成配对';
        debugHtml += '</div>';

        debugHtml += '<table style="width: 100%; border-collapse: collapse;">';
        debugHtml += '<thead><tr style="background: #e9ecef;">';
        debugHtml += '<th style="padding: 8px; border: 1px solid #dee2e6;">标记</th>';
        debugHtml += '<th style="padding: 8px; border: 1px solid #dee2e6;">原图坐标</th>';
        debugHtml += '<th style="padding: 8px; border: 1px solid #dee2e6;">原图颜色</th>';
        debugHtml += '<th style="padding: 8px; border: 1px solid #dee2e6;">SVG坐标</th>';
        debugHtml += '<th style="padding: 8px; border: 1px solid #dee2e6;">X轴偏移</th>';
        debugHtml += '<th style="padding: 8px; border: 1px solid #dee2e6;">Y轴偏移</th>';
        debugHtml += '<th style="padding: 8px; border: 1px solid #dee2e6;">状态</th>';
        debugHtml += '</tr></thead>';
        debugHtml += '<tbody>';

        markerPairs.forEach(pair => {
            const hasOriginal = pair.original !== null;
            const hasSvg = pair.svg !== null;
            const isPaired = hasOriginal && hasSvg;

            let xOffset = '-';
            let yOffset = '-';
            let status = '';
            let statusColor = '';

            if (isPaired) {
                xOffset = (pair.svg.x - pair.original.x).toFixed(2);
                yOffset = (pair.svg.y - pair.original.y).toFixed(2);
                status = '✓ 已配对';
                statusColor = '#28a745';
            } else if (hasOriginal && !hasSvg) {
                status = '等待SVG标记';
                statusColor = '#ffc107';
            } else if (!hasOriginal && hasSvg) {
                status = '仅SVG';
                statusColor = '#17a2b8';
            }

            // 获取原图颜色
            let colorCell = '<span style="color: #999;">-</span>';
            if (hasOriginal && pair.original.color) {
                const rgb = pair.original.color;
                colorCell = `<div style="display: flex; align-items: center; gap: 5px;">
                    <div style="width: 20px; height: 20px; background: rgb(${rgb.r},${rgb.g},${rgb.b}); border: 1px solid #ccc; border-radius: 3px;"></div>
                    <code style="font-size: 0.85em;">#${rgb.hex}</code>
                </div>`;
            }

            debugHtml += '<tr>';
            debugHtml += `<td style="padding: 8px; border: 1px solid #dee2e6; text-align: center;"><strong>#${pair.id}</strong></td>`;
            debugHtml += `<td style="padding: 8px; border: 1px solid #dee2e6;">${hasOriginal ? `(${pair.original.x.toFixed(1)}, ${pair.original.y.toFixed(1)})` : '<span style="color: #999;">未标记</span>'}</td>`;
            debugHtml += `<td style="padding: 8px; border: 1px solid #dee2e6;">${colorCell}</td>`;
            debugHtml += `<td style="padding: 8px; border: 1px solid #dee2e6;">${hasSvg ? `(${pair.svg.x.toFixed(1)}, ${pair.svg.y.toFixed(1)})` : '<span style="color: #999;">未标记</span>'}</td>`;
            debugHtml += `<td style="padding: 8px; border: 1px solid #dee2e6; text-align: center; ${isPaired ? (Math.abs(parseFloat(xOffset)) > 5 ? 'color: #dc3545; font-weight: bold;' : 'color: #28a745;') : ''}">${xOffset}</td>`;
            debugHtml += `<td style="padding: 8px; border: 1px solid #dee2e6; text-align: center; ${isPaired ? (Math.abs(parseFloat(yOffset)) > 5 ? 'color: #dc3545; font-weight: bold;' : 'color: #28a745;') : ''}">${yOffset}</td>`;
            debugHtml += `<td style="padding: 8px; border: 1px solid #dee2e6; text-align: center; color: ${statusColor};">${status}</td>`;
            debugHtml += '</tr>';
        });

        debugHtml += '</tbody></table>';

        // 统计信息
        const pairedCount = markerPairs.filter(p => p.original && p.svg).length;
        const totalMarkers = markerPairs.length;

        debugHtml += `<div style="margin-top: 15px; padding: 10px; background: #e7f3ff; border-radius: 5px; text-align: center;">`;
        debugHtml += `<strong>统计：</strong> 总标记数 ${totalMarkers} | 已配对 ${pairedCount} | 待配对 ${totalMarkers - pairedCount}`;
        debugHtml += '</div>';

        debugContent.innerHTML = debugHtml;
    }

    // 清除所有标记
    function clearMarkers() {
        document.querySelectorAll('.marker').forEach(marker => marker.remove());
        markerPairs = [];
        nextMarkerId = 1;
        console.log('已清除所有标记');
    }
    
    // 标记校验模式切换
    compareBtn.addEventListener('click', function() {
        if (compareBtn.classList.contains('btn-active')) {
            // 关闭标记校验模式
            compareBtn.textContent = '标记校验';
            compareBtn.classList.remove('btn-active');
            clearMarkers();
            debugContent.innerHTML = '<p style="text-align: center; color: #6c757d;">标记校验模式已关闭</p>';
        } else {
            // 开启标记校验模式
            compareBtn.textContent = '关闭校验';
            compareBtn.classList.add('btn-active');

            let debugHtml = '<h3>📍 标记校验模式</h3>';
            debugHtml += '<div style="padding: 15px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid #4361ee;">';
            debugHtml += '<p style="margin: 0 0 10px 0;"><strong>使用方法：</strong></p>';
            debugHtml += '<ol style="margin: 0; padding-left: 20px;">';
            debugHtml += '<li>在<strong>左侧原图</strong>上点击一个位置，会出现🔴红色数字标记</li>';
            debugHtml += '<li>在<strong>右侧SVG</strong>对应位置点击，会出现🔵蓝色相同数字标记</li>';
            debugHtml += '<li>系统会自动计算并显示X轴和Y轴的坐标偏移</li>';
            debugHtml += '<li>偏移大于5像素会以<span style="color: #dc3545; font-weight: bold;">红色</span>高亮显示</li>';
            debugHtml += '</ol>';
            debugHtml += '<p style="margin: 10px 0 0 0; color: #6c757d; font-size: 0.9em;">💡 提示：可以标记多个点来全面对比</p>';
            debugHtml += '</div>';

            debugContent.innerHTML = debugHtml;
        }
    });
    
    // 复制调试信息按钮
    const copyDebugBtn = document.getElementById('copy-debug-btn');
    if (copyDebugBtn) {
        copyDebugBtn.addEventListener('click', function() {
            const debugText = debugContent.innerText || debugContent.textContent;

            // 使用 Clipboard API
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(debugText).then(() => {
                    const originalText = copyDebugBtn.textContent;
                    copyDebugBtn.textContent = '已复制!';
                    copyDebugBtn.style.backgroundColor = '#28a745';
                    setTimeout(() => {
                        copyDebugBtn.textContent = originalText;
                        copyDebugBtn.style.backgroundColor = '';
                    }, 1500);
                }).catch(err => {
                    console.error('复制失败:', err);
                    alert('复制失败，请手动选择文本复制');
                });
            } else {
                // 降级方案：选择文本
                const range = document.createRange();
                range.selectNodeContents(debugContent);
                const selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);
                alert('已选中文本，请按 Ctrl+C (或 Cmd+C) 复制');
            }
        });
    }

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
    
    // Upload functionality
    const uploadArea = document.getElementById('upload-area');
    const imageUpload = document.getElementById('image-upload');
    const uploadForm = document.getElementById('upload-form');
    const uploadResult = document.getElementById('upload-result');
    
    // Click on upload area to trigger file input
    uploadArea.addEventListener('click', function() {
        imageUpload.click();
    });
    
    // Handle drag and drop
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.style.borderColor = 'var(--primary-color)';
        uploadArea.style.backgroundColor = '#f0f4ff';
    });
    
    uploadArea.addEventListener('dragleave', function() {
        uploadArea.style.borderColor = '#ccc';
        uploadArea.style.backgroundColor = 'white';
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.style.borderColor = '#ccc';
        uploadArea.style.backgroundColor = 'white';
        
        if (e.dataTransfer.files.length) {
            imageUpload.files = e.dataTransfer.files;
            // Auto submit the form
            const formData = new FormData();
            formData.append('image', imageUpload.files[0]);
            
            submitUpload(formData);
        }
    });
    
    // Handle form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!imageUpload.files.length) {
            uploadResult.innerHTML = '<p style="color: #dc3545;">请选择一张图片上传</p>';
            return;
        }
        
        const formData = new FormData();
        formData.append('image', imageUpload.files[0]);
        
        submitUpload(formData);
    });
    
    function submitUpload(formData) {
        showLoading();
        
        fetch('/upload_debug_image', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                uploadResult.innerHTML = `<p style="color: #28a745;">图片上传成功！保存路径: ${data.path}</p>`;
                debugContent.innerHTML = '<p style="text-align: center; color: #6c757d;">上传的图片将用于算法调试对比</p>';
            } else {
                uploadResult.innerHTML = `<p style="color: #dc3545;">上传失败: ${data.error}</p>`;
            }
        })
        .catch(error => {
            uploadResult.innerHTML = `<p style="color: #dc3545;">上传错误: ${error.message}</p>`;
        });
    }
});