#!/usr/bin/env python3
"""
SalesBoost 本地环境搭建脚本
Setup Local Development Environment

功能:
1. 初始化SQLite数据库
2. 配置ChromaDB向量库
3. 验证环境配置
"""

import os
import sqlite3
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def setup_sqlite_database():
    """初始化SQLite数据库"""
    print("\n=== Initialize SQLite Database ===")

    db_path = Path("data/databases/salesboost_local.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 创建产品表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        annual_fee REAL,
        benefits TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 创建知识库元数据表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        file_type TEXT,
        chunk_count INTEGER,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        checksum TEXT
    )
    """)

    # 创建对话历史表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dialogue_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        user_message TEXT,
        agent_response TEXT,
        intent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    print(f"[OK] SQLite database created: {db_path}")
    print(f"[OK] Tables: products, knowledge_metadata, dialogue_history")

    return str(db_path)


def setup_chromadb():
    """配置ChromaDB向量库"""
    print("\n=== Configure ChromaDB Vector Store ===")

    try:
        import chromadb
        from chromadb.config import Settings

        # 创建持久化目录
        chroma_path = Path("storage/chromadb")
        chroma_path.mkdir(parents=True, exist_ok=True)

        # 初始化ChromaDB客户端
        client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 创建或获取collection
        try:
            collection = client.get_collection("sales_knowledge")
            print(f"[OK] Existing collection: sales_knowledge")
        except:
            collection = client.create_collection(
                name="sales_knowledge",
                metadata={"description": "销售知识库"}
            )
            print(f"[OK] Created new collection: sales_knowledge")

        print(f"[OK] ChromaDB path: {chroma_path}")
        print(f"[OK] Collection count: {len(client.list_collections())}")

        return str(chroma_path)

    except ImportError:
        print("[X] ChromaDB not installed, please run: pip install chromadb")
        return None


def verify_dependencies():
    """验证依赖包"""
    print("\n=== Verify Dependencies ===")

    required_packages = {
        "chromadb": "Vector database",
        "sentence_transformers": "Text embeddings",
        "pandas": "Data processing",
        "openpyxl": "Excel processing",
        "PyPDF2": "PDF processing",
        "docx": "Word processing"  # Import name is 'docx', not 'python-docx'
    }

    missing_packages = []

    for package, description in required_packages.items():
        try:
            __import__(package.replace("-", "_"))
            print(f"[OK] {package:25s} - {description}")
        except ImportError:
            print(f"[X] {package:25s} - {description} (not installed)")
            missing_packages.append(package)

    if missing_packages:
        print(f"\nMissing packages, please run:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    return True


def create_directory_structure():
    """创建目录结构"""
    print("\n=== Create Directory Structure ===")

    directories = [
        "data/databases",
        "storage/chromadb",
        "data/processed",
        "storage/generated_data",
        "logs",
        "data/seeds"
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"[OK] {directory}")

    return True


def main():
    """主函数"""
    print("="*70)
    print("SalesBoost 本地环境搭建")
    print("="*70)

    # 1. 创建目录结构
    create_directory_structure()

    # 2. 验证依赖
    if not verify_dependencies():
        print("\n[WARN] Please install missing dependencies first")
        return False

    # 3. 初始化SQLite
    db_path = setup_sqlite_database()

    # 4. 配置ChromaDB
    chroma_path = setup_chromadb()

    if chroma_path:
        print("\n" + "="*70)
        print("[OK] Environment setup complete!")
        print("="*70)
        print(f"\nSQLite database: {db_path}")
        print(f"ChromaDB path: {chroma_path}")
        print("\nNext steps:")
        print("1. Run data processing: python scripts/process_sales_data.py")
        print("2. Run data generation: python scripts/generate_training_data.py")
        return True
    else:
        print("\n[X] Environment setup failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
