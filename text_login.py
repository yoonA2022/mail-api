"""测试登录功能的脚本"""
from utils.auth import AuthUtils
from config.database import get_db_connection

def create_test_user():
    """创建测试用户"""
    db = get_db_connection()
    
    # 生成加密密码
    password = "admin123"
    hashed_password = AuthUtils.hash_password(password)
    
    print(f"原始密码: {password}")
    print(f"加密密码: {hashed_password}")
    
    try:
        with db.get_cursor() as cursor:
            # 检查用户是否已存在
            cursor.execute("SELECT id FROM users WHERE email = %s", ("admin@example.com",))
            existing = cursor.fetchone()
            
            if existing:
                print("✅ 测试用户已存在")
                # 更新密码
                cursor.execute(
                    "UPDATE users SET password = %s WHERE email = %s",
                    (hashed_password, "admin@example.com")
                )
                print("✅ 已更新测试用户密码")
            else:
                # 创建新用户
                cursor.execute(
                    """
                    INSERT INTO users 
                    (username, email, password, nickname, role, status, is_verified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    ("admin", "admin@example.com", hashed_password, "系统管理员", "admin", 1, 1)
                )
                print("✅ 已创建测试用户")
            
            print("\n测试账户信息:")
            print("邮箱: admin@example.com")
            print("密码: admin123")
            
    except Exception as e:
        print(f"❌ 错误: {str(e)}")

if __name__ == "__main__":
    create_test_user()
