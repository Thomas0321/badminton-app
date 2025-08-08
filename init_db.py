#!/usr/bin/env python3
import os
import sys

# 设置SECRET_KEY环境变量
os.environ['SECRET_KEY'] = 'badminton_secret_key_2024'

# 导入应用
from app import app, db

def init_database():
    """初始化数据库"""
    try:
        with app.app_context():
            # 删除所有表
            db.drop_all()
            print("已删除所有现有表")
            
            # 创建所有表
            db.create_all()
            print("已创建所有数据表")
            
            # 检查数据库文件是否存在
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if os.path.exists(db_path):
                print(f"数据库文件已创建: {db_path}")
                
                # 检查表结构
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                print(f"创建的表: {tables}")
                
                # 检查User表的列
                if 'user' in tables:
                    columns = inspector.get_columns('user')
                    print("User表的列:")
                    for col in columns:
                        print(f"  - {col['name']}: {col['type']}")
                        
            else:
                print(f"警告：数据库文件未找到: {db_path}")
                
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    init_database()
