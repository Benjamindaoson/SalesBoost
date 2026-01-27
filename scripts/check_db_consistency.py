import asyncio
import logging
from sqlalchemy import text
from core.database import get_db_session_context

logger = logging.getLogger(__name__)

async def check_db_consistency():
    """
    数据库一致性检查脚本
    检查核心表和列是否存在
    """
    required_tables = [
        "courses", "scenario_configs", "customer_personas", 
        "evaluation_dimensions", "knowledge_assets", "knowledge_versions",
        "tenants", "users", "subscriptions", "audit_logs"
    ]
    
    required_columns = {
        "courses": ["tenant_id"],
        "scenario_configs": ["tenant_id"],
        "customer_personas": ["tenant_id"],
        "knowledge_assets": ["tenant_id"],
    }
    
    async with get_db_session_context() as db:
        logger.info("Starting DB consistency check...")
        
        # Check tables
        result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in result.all()]
        
        missing_tables = [t for t in required_tables if t not in tables]
        if missing_tables:
            logger.error(f"❌ Missing tables: {missing_tables}")
            return False
        else:
            logger.info("✅ All required tables present.")
            
        # Check columns (Tenant ID)
        for table, cols in required_columns.items():
            result = await db.execute(text(f"PRAGMA table_info({table});"))
            existing_cols = [row[1] for row in result.all()]
            for col in cols:
                if col not in existing_cols:
                    logger.error(f"❌ Missing column '{col}' in table '{table}'")
                    return False
        
        logger.info("✅ DB consistency check passed.")
        return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(check_db_consistency())
