from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from pydantic import BaseModel

# 引入同级和上级模块
from ..database import get_db
from ..models import User
from ..core.security import verify_password, create_access_token, SECRET_KEY, ALGORITHM

router = APIRouter()

# 1. 定义 OAuth2 认证方案
# tokenUrl 必须指向生成 token 的接口路径，供 Swagger UI 使用
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


# 2. 定义依赖注入函数：获取当前登录用户
# 这个函数就是之前漏掉的，它负责解析 Token 并查库
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码 JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 查询数据库
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


# 3. 登录接口
@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 验证用户名
    user = db.query(User).filter(User.username == form_data.username).first()
    # 验证密码
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成 Token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# 定义请求体模型
class PasswordChange(BaseModel):
    old_password: str
    new_password: str


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
        data: PasswordChange,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. 验证旧密码
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="旧密码错误")

    # 2. 更新新密码
    from ..core.security import get_password_hash  # 确保引入了哈希函数
    current_user.hashed_password = get_password_hash(data.new_password)
    db.add(current_user)
    db.commit()
    return None
