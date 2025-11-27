#!/usr/bin/env python3
"""
自动化轮廓检测优化测试
通过Selenium自动截图并分析，迭代优化轮廓检测算法
"""
import os
import sys
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# 项目路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

TEST_DIR = os.path.join(PROJECT_ROOT, 'test')
SCREENSHOTS_DIR = os.path.join(TEST_DIR, 'screenshots')
ANALYSIS_DIR = os.path.join(TEST_DIR, 'analysis')

# 期望的轮廓配置
EXPECTED_CONTOURS = {
    'body': {'count': 1, 'color': 'red', 'description': '主体外框'},
    'circle_control': {'count': 1, 'color': 'yellow', 'description': '大圆形控制区'},
    'button': {'count': 2, 'color': 'blue/white', 'description': 'MENU和播放按钮'}
}


class ContourOptimizer:
    """轮廓检测优化器"""

    def __init__(self, url='http://127.0.0.1:8000', headless=True):
        self.url = url
        self.headless = headless
        self.driver = None
        self.iteration = 0

    def setup_driver(self):
        """初始化Selenium WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get(self.url)
        print(f"[启动] 浏览器已打开: {self.url}")

    def close_driver(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("[关闭] 浏览器已关闭")

    def click_detect_outline(self):
        """点击'标出轮廓'按钮"""
        try:
            wait = WebDriverWait(self.driver, 10)
            outline_btn = wait.until(
                EC.element_to_be_clickable((By.ID, 'outline-btn'))
            )
            outline_btn.click()
            time.sleep(2)  # 等待轮廓绘制完成
            print("[操作] 已点击'标出轮廓'按钮")
            return True
        except Exception as e:
            print(f"[错误] 点击按钮失败: {e}")
            return False

    def get_debug_info(self):
        """获取调试信息"""
        try:
            debug_content = self.driver.find_element(By.ID, 'debug-content')
            return debug_content.text
        except Exception as e:
            print(f"[错误] 获取调试信息失败: {e}")
            return ""

    def capture_screenshot(self, iteration):
        """截取当前页面截图"""
        screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{iteration}.png")
        self.driver.save_screenshot(screenshot_path)
        print(f"[截图] 已保存: {screenshot_path}")
        return screenshot_path

    def analyze_contours(self, debug_info):
        """分析轮廓检测结果"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'detected_contours': {},
            'issues': [],
            'suggestions': []
        }

        # 解析调试信息
        lines = debug_info.split('\n')
        for line in lines:
            if '检测到的轮廓总数' in line:
                total = line.split(':')[-1].strip()
                analysis['total_contours'] = total
            elif '轮廓类型统计' in line:
                # 提取类型统计
                pass

        # 分析问题
        # TODO: 基于EXPECTED_CONTOURS分析

        return analysis

    def write_analysis(self, iteration, analysis, screenshot_path):
        """写入分析报告"""
        md_path = os.path.join(ANALYSIS_DIR, f"{iteration}.md")

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# 迭代 {iteration} - 轮廓检测分析\n\n")
            f.write(f"**时间**: {analysis['timestamp']}\n\n")
            f.write(f"**截图**: ../screenshots/{iteration}.png\n\n")

            f.write("## 检测结果\n\n")
            f.write(f"- 总轮廓数: {analysis.get('total_contours', 'N/A')}\n")

            if analysis.get('detected_contours'):
                f.write("\n### 各类型轮廓\n\n")
                for ctype, info in analysis['detected_contours'].items():
                    f.write(f"- **{ctype}**: {info}\n")

            if analysis.get('issues'):
                f.write("\n## 发现的问题\n\n")
                for i, issue in enumerate(analysis['issues'], 1):
                    f.write(f"{i}. {issue}\n")

            if analysis.get('suggestions'):
                f.write("\n## 优化建议\n\n")
                for i, suggestion in enumerate(analysis['suggestions'], 1):
                    f.write(f"{i}. {suggestion}\n")

        print(f"[分析] 已保存分析报告: {md_path}")
        return md_path

    def run_iteration(self, iteration):
        """运行单次迭代测试"""
        self.iteration = iteration
        print(f"\n{'='*60}")
        print(f"开始第 {iteration} 轮测试")
        print(f"{'='*60}\n")

        # 1. 刷新页面
        self.driver.refresh()
        time.sleep(2)

        # 2. 点击检测轮廓
        if not self.click_detect_outline():
            return None

        # 3. 获取调试信息
        debug_info = self.get_debug_info()

        # 4. 截图
        screenshot_path = self.capture_screenshot(iteration)

        # 5. 分析结果
        analysis = self.analyze_contours(debug_info)

        # 6. 写入分析报告
        md_path = self.write_analysis(iteration, analysis, screenshot_path)

        return analysis

    def optimize_algorithm(self, analysis):
        """基于分析结果自动优化算法"""
        # TODO: 实现自动代码调整逻辑
        print("[优化] 分析完成，需要手动调整算法参数")
        return False

    def run(self, max_iterations=20):
        """运行完整的优化流程"""
        try:
            self.setup_driver()

            for i in range(1, max_iterations + 1):
                analysis = self.run_iteration(i)

                if analysis is None:
                    print(f"[跳过] 第 {i} 轮测试失败")
                    continue

                # 检查是否需要优化
                if self.optimize_algorithm(analysis):
                    print(f"[优化] 第 {i} 轮：算法已优化，重启服务器...")
                    # TODO: 重启Flask服务器
                    time.sleep(3)
                else:
                    print(f"[完成] 第 {i} 轮测试完成")

                # 等待一段时间再进行下一轮
                time.sleep(1)

            print(f"\n{'='*60}")
            print(f"✓ 完成全部 {max_iterations} 轮测试")
            print(f"{'='*60}\n")

        finally:
            self.close_driver()


if __name__ == '__main__':
    optimizer = ContourOptimizer(headless=False)
    optimizer.run(max_iterations=20)
