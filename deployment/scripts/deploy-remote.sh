#!/bin/bash
# 远程部署脚本 - 在服务器上执行

set -e

echo "==================================="
echo "SalesBoost 远程部署开始"
echo "==================================="

cd /root/salesboost

# 创建main.py
cat > main.py << 'MAINEOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os

app = FastAPI(title="SalesBoost API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    db_path = "/app/data/salesboost.db"
    os.makedirs("/app/data", exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        company TEXT,
        phone TEXT,
        email TEXT,
        status TEXT DEFAULT 'lead',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

class CustomerCreate(BaseModel):
    name: str
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str = "lead"

class CustomerResponse(BaseModel):
    id: int
    name: str
    company: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    status: str
    created_at: str
    updated_at: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SalesBoost Backend"}

@app.get("/api/v1/customers", response_model=List[CustomerResponse])
async def get_customers():
    conn = sqlite3.connect("/app/data/salesboost.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "company": r[2], "phone": r[3], "email": r[4], "status": r[5], "created_at": r[6], "updated_at": r[7]} for r in rows]

@app.post("/api/v1/customers", response_model=CustomerResponse)
async def create_customer(customer: CustomerCreate):
    conn = sqlite3.connect("/app/data/salesboost.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO customers (name, company, phone, email, status) VALUES (?, ?, ?, ?, ?)",
                   (customer.name, customer.company, customer.phone, customer.email, customer.status))
    conn.commit()
    customer_id = cursor.lastrowid
    cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    row = cursor.fetchone()
    conn.close()
    return {"id": row[0], "name": row[1], "company": row[2], "phone": row[3], "email": row[4], "status": row[5], "created_at": row[6], "updated_at": row[7]}

@app.put("/api/v1/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(customer_id: int, customer: CustomerCreate):
    conn = sqlite3.connect("/app/data/salesboost.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE customers SET name=?, company=?, phone=?, email=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                   (customer.name, customer.company, customer.phone, customer.email, customer.status, customer_id))
    conn.commit()
    cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"id": row[0], "name": row[1], "company": row[2], "phone": row[3], "email": row[4], "status": row[5], "created_at": row[6], "updated_at": row[7]}

@app.delete("/api/v1/customers/{customer_id}")
async def delete_customer(customer_id: int):
    conn = sqlite3.connect("/app/data/salesboost.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()
    return {"message": "Customer deleted successfully"}

init_db()
MAINEOF

echo "main.py已创建"

# 清理并启动服务
docker-compose -f docker-production.yml down -v 2>/dev/null || true
docker-compose -f docker-production.yml up -d

echo "等待服务启动..."
sleep 20

echo "==================================="
echo "部署完成!"
echo "访问地址: http://101.43.199.144"
echo "后端API: http://101.43.199.144/api"
echo "==================================="

# 检查服务状态
docker ps --filter "name=salesboost"
