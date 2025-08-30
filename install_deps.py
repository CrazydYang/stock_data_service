#!/usr/bin/env python3
"""
简化版依赖安装脚本
"""

import subprocess
import sys

def install_package(package):
    """安装单个包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--break-system-packages"])
        print(f"✓ 成功安装 {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 安装 {package} 失败: {e}")
        return False

def main():
    """主函数"""
    packages = [
        "flask==2.3.3",
        "flask-cors==4.0.0",
        "pandas>=1.5.0,<2.1.0",
        "numpy>=1.21.0,<1.25.0",
        "requests==2.31.0",
        "akshare==1.11.96",
        "python-dateutil==2.8.2",
        "pytz==2023.3",
        "loguru==0.7.2"
    ]
    
    print("开始安装依赖...")
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n安装完成: {success_count}/{len(packages)} 个包成功")
    
    if success_count == len(packages):
        print("所有依赖安装成功！")
    else:
        print("部分依赖安装失败，但应用可能仍可运行")

if __name__ == "__main__":
    main()