import re

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, ValidationError, field_validator

# FastAPI 앱 인스턴스 생성
app = FastAPI(
    title="실내운전연습장 예약 관리 시스템",
    description="사용자 ID로 전화번호를 사용하는 API 예제입니다.",
    version="1.0.0",
)

# --- 템플릿 설정 ---
# 'templates' 폴더를 템플릿 디렉토리로 설정합니다.
templates = Jinja2Templates(directory="templates")


# --- 유효성 검사를 위한 설정 ---

# 사용자로부터 제공받은 전화번호 정규표현식
PHONE_NUMBER_REGEX = r"^\d{2,4}-?\d{3,4}-?\d{4}$"


# --- Pydantic 모델 정의 ---


# 사용자 생성을 위한 요청 본문(Request Body) 모델
class UserCreate(BaseModel):
    """사용자 생성을 위한 데이터 모델"""

    phone_number: str = Field(
        ...,
        pattern=PHONE_NUMBER_REGEX,
        title="사용자 전화번호 (ID)",
        description="하이픈(-)을 포함하거나 포함하지 않은 전화번호 형식. 예: 010-1234-5678 또는 01012345678",
        example="010-1234-5678",
    )
    name: str = Field(
        ..., min_length=2, max_length=50, title="사용자 이름", example="홍길동"
    )

    @field_validator("phone_number")
    def standardize_phone_number(cls, value):
        return value.replace("-", "")


class UserResponse(BaseModel):
    """사용자 정보 반환을 위한 응답 모델"""

    phone_number: str
    name: str
    message: str


# --- API 엔드포인트 정의 ---


@app.get("/", summary="루트 경로")
async def read_root():
    """서버가 정상적으로 실행 중인지 확인하는 간단한 메시지를 반환합니다."""
    return {"message": "실내운전연습장 예약 관리 시스템에 오신 것을 환영합니다."}


# --- HTML Form을 위한 엔드포인트 ---


@app.get("/register", response_class=HTMLResponse, summary="사용자 등록 폼 페이지")
async def show_register_form(request: Request, message: str = None, error: str = None):
    """
    사용자 등록을 위한 HTML 폼을 렌더링하여 보여줍니다.
    성공 또는 에러 메시지를 쿼리 파라미터로 받아 템플릿에 전달할 수 있습니다.
    """
    return templates.TemplateResponse(
        "register.html", {"request": request, "message": message, "error": error}
    )


@app.post("/register", response_class=HTMLResponse, summary="사용자 등록 처리 (Form)")
async def handle_registration_form(
    request: Request, phone_number: str = Form(...), name: str = Form(...)
):
    """
    HTML 폼에서 제출된 데이터로 사용자를 등록합니다.
    """
    try:
        # Pydantic 모델을 사용하여 데이터 유효성 검사 및 정제
        user_data = UserCreate(phone_number=phone_number, name=name)

        # 실제 애플리케이션에서는 이 부분에 데이터베이스 저장 로직이 들어갑니다.
        print(
            f"폼을 통해 새로운 사용자 등록 시도: {user_data.name} ({user_data.phone_number})"
        )

        # 성공 시 메시지와 함께 등록 폼으로 다시 리다이렉트합니다.
        success_message = f"사용자 '{user_data.name}'님({user_data.phone_number})이 성공적으로 등록되었습니다."
        return RedirectResponse(
            url=f"/register?message={success_message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValidationError as e:
        # 유효성 검사 실패 시, 보다 사용자 친화적인 에러 메시지를 생성합니다.
        error_details = e.errors()[0]  # 첫 번째 에러 정보를 가져옵니다.
        field = error_details.get("loc", ("unknown",))[0]

        if field == "phone_number":
            error_message = "전화번호 형식이 올바르지 않습니다. (예: 010-1234-5678)"
        elif field == "name":
            if error_details.get("type") == "string_too_short":
                error_message = f"이름은 최소 {error_details.get('ctx', {}).get('min_length', 2)}자 이상이어야 합니다."
            else:
                error_message = "이름을 확인해주세요."
        else:
            # 기타 다른 유효성 검사 에러를 위한 기본 메시지
            error_message = "입력값을 확인해주세요."

        # 사용자가 입력했던 값을 그대로 보여주기 위해 context에 담아 전달합니다.
        context = {
            "request": request,
            "error": error_message,
            "phone_number": phone_number,
            "name": name,
        }
        return templates.TemplateResponse(
            "register.html", context, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


# --- 기존 JSON API 엔드포인트 ---


@app.post(
    "/users/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="신규 사용자 등록 (API)",
)
async def create_user_api(user: UserCreate):
    """
    (API용) 새로운 사용자를 시스템에 등록합니다.
    - **phone_number**: 사용자의 ID로 사용될 전화번호입니다.
    - **name**: 사용자의 이름입니다.
    """
    print(f"API를 통해 새로운 사용자 등록 시도: {user.name} ({user.phone_number})")

    return UserResponse(
        phone_number=user.phone_number,
        name=user.name,
        message=f"사용자 '{user.name}'님이 성공적으로 등록되었습니다.",
    )
