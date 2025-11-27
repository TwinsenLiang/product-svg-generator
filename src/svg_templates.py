"""
SVG模板和样式定义
"""

# SVG滤镜和样式定义
SVG_DEFS = '''  <defs>
    <!-- 主体渐变：从浅灰到深灰的自然过渡 -->
    <linearGradient id="remoteGradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#6b6b6b;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#4a4a4a;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#2a2a2a;stop-opacity:1" />
    </linearGradient>

    <!-- 立体光泽渐变 -->
    <linearGradient id="glossGradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:rgba(255,255,255,0.1);stop-opacity:1" />
      <stop offset="50%" style="stop-color:rgba(255,255,255,0.2);stop-opacity:1" />
      <stop offset="100%" style="stop-color:rgba(255,255,255,0.1);stop-opacity:1" />
    </linearGradient>

    <!-- 投影滤镜 -->
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="4"/>
      <feOffset dx="2" dy="4" result="offsetblur"/>
      <feFlood flood-color="rgba(0,0,0,0.4)"/>
      <feComposite in2="offsetblur" operator="in"/>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <!-- 立体浮雕滤镜 -->
    <filter id="bevel" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="blur"/>
      <feSpecularLighting in="blur" surfaceScale="5" specularConstant="0.8" specularExponent="15" lighting-color="#ffffff" result="spec">
        <fePointLight x="-5000" y="-10000" z="25000"/>
      </feSpecularLighting>
      <feComposite in="spec" in2="SourceGraphic" operator="in" result="comp"/>
      <feComposite in="SourceGraphic" in2="comp" operator="arithmetic" k1="0" k2="1" k3="1" k4="0"/>
    </filter>
  </defs>'''

def generate_remote_body(x, y, w, h, rx, ry):
    """
    生成遥控器主体SVG元素

    Args:
        x, y: 位置坐标
        w, h: 宽度和高度
        rx, ry: 圆角半径

    Returns:
        SVG元素字符串
    """
    # 计算高光区域参数
    highlight_height = max(30, int(h * 0.15))  # 高光高度为总高度的15%，最小30px

    return f'''  <!-- 主体底色带渐变 -->
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}"
        fill="url(#remoteGradient)"
        stroke="#0a0a0a"
        stroke-width="2"
        filter="url(#shadow)"/>

  <!-- 立体浮雕效果 -->
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}"
        fill="url(#remoteGradient)"
        stroke="none"
        style="filter: url(#bevel)"/>

  <!-- 顶部主高光区域 -->
  <rect x="{x + 3}" y="{y + 3}" width="{w - 6}" height="{highlight_height}"
        rx="{max(3, rx - 3)}" ry="{max(3, ry - 3)}"
        fill="url(#glossGradient)"
        opacity="0.6"/>

  <!-- 顶部细高光线 -->
  <rect x="{x + 5}" y="{y + 5}" width="{w - 10}" height="3"
        rx="2" ry="2"
        fill="rgba(255,255,255,0.3)"/>

  <!-- 左侧边缘高光 -->
  <rect x="{x + 2}" y="{y + int(h * 0.1)}" width="1.5" height="{int(h * 0.8)}"
        fill="rgba(255,255,255,0.1)"/>

  <!-- 右侧边缘阴影 -->
  <rect x="{x + w - 3}" y="{y + int(h * 0.1)}" width="1.5" height="{int(h * 0.8)}"
        fill="rgba(0,0,0,0.2)"/>'''

def generate_radial_gradients_from_grid(color_grid):
    """
    基于颜色网格生成径向渐变定义

    Args:
        color_grid: 颜色点列表 [{'x': x, 'y': y, 'hex': '#rrggbb'}, ...]

    Returns:
        SVG径向渐变定义字符串
    """
    gradients = []
    for idx, point in enumerate(color_grid):
        grad_id = f"radial_{idx}"
        gradients.append(f'''    <radialGradient id="{grad_id}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#{point['hex']};stop-opacity:0.8" />
      <stop offset="100%" style="stop-color:#{point['hex']};stop-opacity:0" />
    </radialGradient>''')

    return '\n'.join(gradients)

def generate_grid_circles(color_grid, radius=15):
    """
    基于颜色网格生成圆形元素

    Args:
        color_grid: 颜色点列表
        radius: 每个圆的半径

    Returns:
        SVG圆形元素字符串
    """
    circles = []
    for idx, point in enumerate(color_grid):
        grad_id = f"radial_{idx}"
        circles.append(f'  <circle cx="{point["x"]}" cy="{point["y"]}" r="{radius}" fill="url(#{grad_id})"/>')

    return '\n'.join(circles)

def create_svg_document(width, height, content, comment=""):
    """
    创建完整的SVG文档

    Args:
        width, height: SVG画布尺寸
        content: SVG内容
        comment: 可选的注释

    Returns:
        完整的SVG文档字符串
    """
    comment_line = f"  <!-- {comment} -->\n" if comment else ""
    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
{comment_line}{SVG_DEFS}

{content}
</svg>'''
