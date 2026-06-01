from datetime import datetime

from pydantic import BaseModel, Field


# ===== User =====
class UserCreate(BaseModel):
    account: str = Field(..., min_length=3, max_length=64)
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    email: str | None = None
    role: str = "student"


class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    account: str
    username: str
    email: str | None
    role: str
    is_active: bool
    create_time: datetime | None
    update_time: datetime | None

    model_config = {"from_attributes": True}


# ===== Task =====
class TaskCreate(BaseModel):
    task_id: str
    user_id: int
    subject: str | None = None
    grade: str | None = None
    mode: str
    status: str = "pending"


class TaskUpdate(BaseModel):
    subject: str | None = None
    grade: str | None = None
    status: str | None = None


class TaskOut(BaseModel):
    id: int
    task_id: str
    user_id: int
    subject: str | None
    grade: str | None
    mode: str
    status: str
    create_time: datetime | None
    update_time: datetime | None

    model_config = {"from_attributes": True}


# ===== Image =====
class ImageCreate(BaseModel):
    task_id: str
    url: str


class ImageOut(BaseModel):
    id: int
    task_id: str
    url: str
    create_time: datetime | None

    model_config = {"from_attributes": True}


# ===== Question =====
class QuestionCreate(BaseModel):
    task_id: str
    no: str
    question_text: str | None = None
    student_answer: str | None = None
    question_type: str | None = None


class QuestionUpdate(BaseModel):
    question_text: str | None = None
    student_answer: str | None = None
    question_type: str | None = None


class QuestionOut(BaseModel):
    id: int
    task_id: str
    no: str
    question_text: str | None
    student_answer: str | None
    question_type: str | None
    create_time: datetime | None

    model_config = {"from_attributes": True}


# ===== Block =====
class BlockCreate(BaseModel):
    question_id: int | None = None
    url: str
    x1: int
    y1: int
    x2: int
    y2: int


class BlockOut(BaseModel):
    id: int
    question_id: int | None
    url: str
    x1: int
    y1: int
    x2: int
    y2: int
    create_time: datetime | None

    model_config = {"from_attributes": True}


# ===== Correction =====
class CorrectionCreate(BaseModel):
    question_id: int
    score: float
    result: str
    comment: str | None = None
    analysis: str | None = None


class CorrectionUpdate(BaseModel):
    score: float | None = None
    result: str | None = None
    comment: str | None = None
    analysis: str | None = None


class CorrectionOut(BaseModel):
    id: int
    question_id: int
    score: float
    result: str
    comment: str | None
    analysis: str | None
    create_time: datetime | None

    model_config = {"from_attributes": True}


# ===== Knowledge =====
class KnowledgeCreate(BaseModel):
    user_id: int
    title: str
    url: str
    subject: str | None = None
    grade: str | None = None


class KnowledgeUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    grade: str | None = None
    status: str | None = None


class KnowledgeOut(BaseModel):
    id: int
    user_id: int
    title: str
    url: str
    subject: str | None
    grade: str | None
    status: str
    chunk: int
    create_time: datetime | None

    model_config = {"from_attributes": True}


# ===== QuestionChunk =====
class QuestionChunkCreate(BaseModel):
    question_id: int
    knowledge_id: int
    chunk_id: str


class QuestionChunkOut(BaseModel):
    id: int
    question_id: int
    knowledge_id: int
    chunk_id: str
    create_time: datetime | None

    model_config = {"from_attributes": True}


# ===== Model =====
class ModelCreate(BaseModel):
    name: str
    mode: int


class ModelOut(BaseModel):
    id: int
    name: str
    mode: int

    model_config = {"from_attributes": True}


# ===== Config =====
class ConfigCreate(BaseModel):
    user_id: int
    rec_mode: str = "aliyun"
    vl_model: str | None = None
    gl_model: str | None = None


class ConfigUpdate(BaseModel):
    rec_mode: str | None = None
    vl_model: str | None = None
    gl_model: str | None = None


class ConfigOut(BaseModel):
    id: int
    user_id: int
    rec_mode: str
    vl_model: str | None
    gl_model: str | None
    create_time: datetime | None
    update_time: datetime | None

    model_config = {"from_attributes": True}
