from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.domain.models import TransactionCreate, UserCreate, UserUpdatePassword, UserResponse, UserRole, UserUpdate
from app.application.service import TransactionService
from app.application.user_service import UserService
from app.infrastructure.persistence.outbox import OutboxPublisher
from app.infrastructure.persistence.models import UserDB
from app.infrastructure.persistence.auth import decode_access_token, create_access_token, verify_password
import structlog
import uuid

router = APIRouter()
logger = structlog.get_logger()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await UserDB.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await UserDB.get_or_none(email=form_data.username)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    user_service: UserService = Depends(UserService)
):
    try:
        user = await user_service.create_user(data)
        return user
    except Exception as e:
        logger.error("api_user_creation_failed", error=str(e), email=data.email)
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/users/password")
async def update_password(
    data: UserUpdatePassword,
    current_user: UserDB = Depends(get_current_user),
    user_service: UserService = Depends(UserService)
):
    try:
        await user_service.update_password(current_user.id, data)
        return {"message": "Password updated successfully"}
    except Exception as e:
        logger.error("api_password_update_failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/users/me", response_model=UserResponse)
async def update_profile(
    data: UserUpdate,
    current_user: UserDB = Depends(get_current_user),
    user_service: UserService = Depends(UserService)
):
    try:
        user = await user_service.update_profile(current_user.id, data)
        return user
    except Exception as e:
        logger.error("api_profile_update_failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: UserDB = Depends(get_current_user),
    user_service: UserService = Depends(UserService)
):
    try:
        return await user_service.list_users(current_user.role)
    except Exception as e:
        logger.error("api_list_users_failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/transactions", status_code=201)
async def create_transaction(
    data: TransactionCreate,
    current_user: UserDB = Depends(get_current_user),
    service: TransactionService = Depends(TransactionService)
):
    try:
        transaction = await service.process_transaction(data, current_user.id)
        return transaction
    except Exception as e:
        logger.error("api_transaction_failed", error=str(e), transaction_id=data.transaction_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions")
async def list_transactions(
    current_user: UserDB = Depends(get_current_user),
    service: TransactionService = Depends(TransactionService)
):
    try:
        return await service.list_user_transactions(current_user.id, current_user.role)
    except Exception as e:
        logger.error("api_list_transactions_failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def exclude_user(
    user_id: uuid.UUID,
    current_user: UserDB = Depends(get_current_user),
    user_service: UserService = Depends(UserService)
):
    try:
        await user_service.exclude_user(user_id, current_user.role, current_user.id)
        return None
    except Exception as e:
        logger.error("api_exclude_user_failed", error=str(e), user_id=str(user_id), actor_id=str(current_user.id))
        if "Unauthorized" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
