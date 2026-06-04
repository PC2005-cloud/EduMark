import re

from datetime import datetime

from pydantic import BaseModel, Field

EMAIL_PATTERN = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class LoginSchema(BaseModel):
    account: str = Field(..., min_length=3, max_length=64, description="用户账号，3~64 个字符")
    password: str = Field(..., min_length=6, max_length=128, description="用户密码，6~128 个字符")


class RefreshSchema(BaseModel):
    token: str = Field(..., min_length=1, description="刷新令牌（refresh_token）")


# ===== Auth Token =====
class TokenResponse(BaseModel):
    access_token: str = Field(description="访问令牌，有效期 120 分钟")
    refresh_token: str = Field(description="刷新令牌，有效期 7 天")
    token_type: str = Field(description="令牌类型，固定为 bearer")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    }


class SubmitResponse(BaseModel):
    task_id: str = Field(description="提交成功后分配的任务唯一标识")

    model_config = {
        "json_schema_extra": {
            "example": {"task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
        }
    }


class StatusResponse(BaseModel):
    task_id: str = Field(description="任务唯一标识")
    status: str = Field(description="当前状态：pending=待处理，processing=处理中，completed=已完成，failed=失败")

    model_config = {
        "json_schema_extra": {
            "example": {"task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "status": "completed"}
        }
    }


class CurrentUser(BaseModel):
    id: int = Field(description="用户 ID")
    role: str = Field(description="用户角色：student 或 teacher 或 admin")
    account: str = Field(description="用户账号")


# ===== User =====
class UserCreate(BaseModel):
    account: str = Field(..., min_length=3, max_length=64, description="用户账号，3~64 个字符")
    username: str = Field(..., min_length=1, max_length=64, description="用户昵称，1~64 个字符")
    password: str = Field(..., min_length=6, max_length=128, description="用户密码，6~128 个字符")
    email: str | None = Field(None, description="电子邮箱，可选")
    role: str = Field("student", pattern=r"^(student|teacher)$", description="用户角色：student=学生，teacher=老师")


class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=1, max_length=64, description="用户昵称")
    email: str | None = Field(None, max_length=128, pattern=EMAIL_PATTERN, description="电子邮箱")
    is_active: bool | None = Field(None, description="是否启用，true=启用，false=禁用")


class UserOut(BaseModel):
    id: int = Field(description="用户 ID")
    account: str = Field(description="用户账号")
    username: str = Field(description="用户昵称")
    email: str | None = Field(None, description="电子邮箱")
    role: str = Field(description="用户角色：student 或 teacher")
    is_active: bool = Field(description="是否启用")
    create_time: datetime | None = Field(None, description="创建时间")
    update_time: datetime | None = Field(None, description="最后更新时间")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "account": "zhangsan",
                "username": "张三",
                "email": "zhangsan@example.com",
                "role": "student",
                "is_active": True,
                "create_time": "2026-06-01T08:00:00",
                "update_time": "2026-06-04T12:00:00",
            }
        },
    }


# ===== Task =====
class TaskCreate(BaseModel):
    task_id: str = Field(description="任务唯一标识")
    user_id: int = Field(description="所属用户 ID")
    subject: str | None = Field(None, description="科目，如语文、数学、英语等")
    grade: str | None = Field(None, description="年级，如一年级、二年级等")
    mode: str = Field(description="批改模式：aliyun=阿里云，或百炼视觉模型名如 qwen-vl-plus")
    status: str = Field("pending", description="任务状态：pending=待处理，processing=处理中，completed=已完成，failed=失败")


class TaskUpdate(BaseModel):
    subject: str | None = Field(None, description="科目")
    grade: str | None = Field(None, description="年级")
    status: str | None = Field(None, description="任务状态")


class TaskOut(BaseModel):
    id: int = Field(description="任务记录 ID")
    task_id: str = Field(description="任务唯一标识")
    user_id: int = Field(description="所属用户 ID")
    subject: str | None = Field(None, description="科目")
    grade: str | None = Field(None, description="年级")
    mode: str = Field(description="批改模式：aliyun=阿里云，或百炼视觉模型名")
    status: str = Field(description="任务状态：pending=待处理，processing=处理中，completed=已完成，failed=失败")
    create_time: datetime | None = Field(None, description="创建时间")
    update_time: datetime | None = Field(None, description="最后更新时间")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "user_id": 1,
                "subject": "数学",
                "grade": "二年级",
                "mode": "aliyun",
                "status": "completed",
                "create_time": "2026-06-04T10:00:00",
                "update_time": "2026-06-04T10:05:00",
            }
        },
    }


# ===== Image =====
class ImageCreate(BaseModel):
    task_id: str = Field(description="所属任务 ID")
    url: str = Field(description="图片存储路径")


class ImageOut(BaseModel):
    id: int = Field(description="图片记录 ID")
    task_id: str = Field(description="所属任务 ID")
    url: str = Field(description="图片存储路径")
    create_time: datetime | None = Field(None, description="创建时间")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "url": "homework/1/1717488000_math_homework.jpg",
                "create_time": "2026-06-04T10:00:00",
            }
        },
    }


# ===== Question =====
class QuestionCreate(BaseModel):
    task_id: str = Field(description="所属任务 ID")
    no: str = Field(description="题号")
    question_text: str | None = Field(None, description="题目文本")
    student_answer: str | None = Field(None, description="学生答案")
    question_type: str | None = Field(None, description="题目类型")


class QuestionUpdate(BaseModel):
    question_text: str | None = Field(None, description="题目文本")
    student_answer: str | None = Field(None, description="学生答案")
    question_type: str | None = Field(None, description="题目类型")


class QuestionOut(BaseModel):
    id: int = Field(description="题目记录 ID")
    task_id: str = Field(description="所属任务 ID")
    no: str = Field(description="题号")
    question_text: str | None = Field(None, description="题目文本")
    student_answer: str | None = Field(None, description="学生答案")
    question_type: str | None = Field(None, description="题目类型")
    create_time: datetime | None = Field(None, description="创建时间")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "no": "1",
                "question_text": "小明有12个苹果，吃了3个，又买了5个，现在有多少个苹果？",
                "student_answer": "14个",
                "question_type": "应用题",
                "create_time": "2026-06-04T10:01:00",
            }
        },
    }


# ===== Block =====
class BlockCreate(BaseModel):
    question_id: int | None = Field(None, description="所属题目 ID，可选")
    url: str = Field(description="裁切块图片存储路径")
    x1: float = Field(description="裁切区域左上角 X 坐标")
    y1: float = Field(description="裁切区域左上角 Y 坐标")
    x2: float = Field(description="裁切区域右下角 X 坐标")
    y2: float = Field(description="裁切区域右下角 Y 坐标")


class BlockOut(BaseModel):
    id: int = Field(description="裁切块记录 ID")
    question_id: int | None = Field(None, description="所属题目 ID")
    url: str = Field(description="裁切块所属原始图片的存储路径")
    x1: float = Field(description="裁切区域左上角 X 坐标（百分比，范围 0~1）")
    y1: float = Field(description="裁切区域左上角 Y 坐标（百分比，范围 0~1）")
    x2: float = Field(description="裁切区域右下角 X 坐标（百分比，范围 0~1）")
    y2: float = Field(description="裁切区域右下角 Y 坐标（百分比，范围 0~1）")
    create_time: datetime | None = Field(None, description="创建时间")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "question_id": 1,
                "url": "homework/1/1717488000_math_homework.jpg",
                "x1": 0.12,
                "y1": 0.08,
                "x2": 0.65,
                "y2": 0.35,
                "create_time": "2026-06-04T10:01:00",
            }
        },
    }


# ===== Correction =====
class CorrectionCreate(BaseModel):
    question_id: int = Field(description="所属题目 ID")
    score: float = Field(description="得分")
    result: str = Field(description="批改结果标识")
    comment: str | None = Field(None, description="评语")
    analysis: str | None = Field(None, description="错因分析")


class CorrectionUpdate(BaseModel):
    score: float | None = Field(None, description="得分")
    result: str | None = Field(None, description="批改结果标识")
    comment: str | None = Field(None, description="评语")
    analysis: str | None = Field(None, description="错因分析")


class CorrectionOut(BaseModel):
    id: int = Field(description="批改记录 ID")
    question_id: int = Field(description="所属题目 ID")
    score: float = Field(description="得分（满分 10 分）")
    result: str = Field(description="批改结果：correct=正确，wrong=错误，partial=部分正确")
    comment: str | None = Field(None, description="评语")
    analysis: str | None = Field(None, description="错因分析")
    create_time: datetime | None = Field(None, description="创建时间")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "question_id": 1,
                "score": 10.0,
                "result": "correct",
                "comment": "回答正确，计算过程无误",
                "analysis": "12-3+5=14，先减后加，运算顺序正确",
                "create_time": "2026-06-04T10:05:00",
            }
        },
    }


# ===== Knowledge =====
class KnowledgeCreate(BaseModel):
    user_id: int = Field(description="所属用户 ID")
    title: str = Field(description="知识文档标题")
    url: str = Field(description="知识文档存储路径")
    subject: str | None = Field(None, description="科目")
    grade: str | None = Field(None, description="年级")


class KnowledgeUpdate(BaseModel):
    title: str | None = Field(None, description="知识文档标题")
    subject: str | None = Field(None, description="科目")
    grade: str | None = Field(None, description="年级")
    status: str | None = Field(None, description="文档状态：pending=待处理，parsing=解析中，completed=已完成，failed=失败")


class KnowledgeOut(BaseModel):
    id: int = Field(description="知识文档 ID")
    user_id: int = Field(description="所属用户 ID")
    title: str = Field(description="知识文档标题")
    url: str = Field(description="知识文档存储路径")
    subject: str | None = Field(None, description="科目")
    grade: str | None = Field(None, description="年级")
    status: str = Field(description="文档状态：pending=待处理，parsing=解析中，completed=已完成，failed=失败")
    chunk: int = Field(description="解析后分块数量")
    create_time: datetime | None = Field(None, description="创建时间")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "user_id": 2,
                "title": "二年级数学知识点汇总.pdf",
                "url": "knowledge/2/1717488000_math_knowledge.pdf",
                "subject": "数学",
                "grade": "二年级",
                "status": "completed",
                "chunk": 15,
                "create_time": "2026-06-04T09:00:00",
            }
        },
    }


# ===== QuestionChunk =====
class QuestionChunkCreate(BaseModel):
    question_id: int = Field(description="所属题目 ID")
    knowledge_id: int = Field(description="关联知识文档 ID")
    chunk_id: str = Field(description="知识文档中匹配的分块 ID")


class QuestionChunkOut(BaseModel):
    id: int = Field(description="关联记录 ID")
    question_id: int = Field(description="所属题目 ID")
    knowledge_id: int = Field(description="关联知识文档 ID")
    chunk_id: str = Field(description="Qdrant 中匹配的知识分块 ID")
    create_time: datetime | None = Field(None, description="创建时间")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "question_id": 1,
                "knowledge_id": 1,
                "chunk_id": "10000",
                "create_time": "2026-06-04T10:05:00",
            }
        },
    }


# ===== Model =====
class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="模型名称，1~64 个字符")
    mode: int = Field(..., ge=1, le=2, description="模型类型：1=视觉模型，2=语言模型")


class ModelOut(BaseModel):
    id: int = Field(description="模型记录 ID")
    name: str = Field(description="模型名称")
    mode: int = Field(description="模型类型：1=视觉模型，2=语言模型")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "qwen-vl-max",
                "mode": 1,
            }
        },
    }


# ===== Config =====
class ConfigUpdate(BaseModel):
    rec_mode: str | None = Field(None, pattern=r"^(aliyun|bailian)$", description="识别模式：aliyun=阿里云，bailian=百炼")
    enable_enhance: bool | None = Field(None, description="是否启用增强功能")
    enable_knowledge: bool | None = Field(None, description="是否启用知识库")
    vl_model: str | None = Field(None, max_length=64, description="视觉模型名称")
    gl_model: str | None = Field(None, max_length=64, description="语言模型名称")


class ConfigOut(BaseModel):
    id: int = Field(description="配置记录 ID")
    user_id: int = Field(description="所属用户 ID")
    rec_mode: str = Field(description="识别模式")
    enable_enhance: bool = Field(description="是否启用增强功能")
    enable_knowledge: bool = Field(description="是否启用知识库")
    vl_model: str | None = Field(None, description="视觉模型名称")
    gl_model: str | None = Field(None, description="语言模型名称")
    create_time: datetime | None = Field(None, description="创建时间")
    update_time: datetime | None = Field(None, description="最后更新时间")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "user_id": 1,
                "rec_mode": "aliyun",
                "enable_enhance": True,
                "enable_knowledge": True,
                "vl_model": "qwen-vl-max",
                "gl_model": "qwen-max",
                "create_time": "2026-06-01T08:00:00",
                "update_time": "2026-06-04T12:00:00",
            }
        },
    }


# ===== Homework Result =====
class BlockInfo(BaseModel):
    url: str = Field("", description="裁切块所属原始图片的访问地址")
    x1: float = Field(description="裁切区域左上角 X 坐标（百分比，范围 0~1）")
    y1: float = Field(description="裁切区域左上角 Y 坐标（百分比，范围 0~1）")
    x2: float = Field(description="裁切区域右下角 X 坐标（百分比，范围 0~1）")
    y2: float = Field(description="裁切区域右下角 Y 坐标（百分比，范围 0~1）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://minio.example.com/homework/1/1717488000_math_homework.jpg",
                "x1": 0.12,
                "y1": 0.08,
                "x2": 0.65,
                "y2": 0.35,
            }
        }
    }


class CorrectionInfo(BaseModel):
    score: float = Field(description="得分（满分 10 分）")
    result: str = Field(description="批改结果：correct=正确，wrong=错误，partial=部分正确")
    comment: str | None = Field(None, description="评语")
    analysis: str | None = Field(None, description="错因分析")

    model_config = {
        "json_schema_extra": {
            "example": {
                "score": 10.0,
                "result": "correct",
                "comment": "回答正确，计算过程无误",
                "analysis": "12-3+5=14，先减后加，运算顺序正确",
            }
        }
    }


class KnowledgeRef(BaseModel):
    knowledge_id: int = Field(description="关联知识文档 ID")
    title: str = Field(description="知识文档标题")
    content: str = Field(description="匹配到的知识分块内容")
    score: float = Field(description="匹配相关度得分")

    model_config = {
        "json_schema_extra": {
            "example": {
                "knowledge_id": 1,
                "title": "二年级数学知识点汇总.pdf",
                "content": "加减混合运算：在没有括号的算式里，只有加减法，要从左往右按顺序计算，也可以运用加法交换律和结合律进行简便计算。",
                "score": 0.95,
            }
        }
    }


class QuestionResult(BaseModel):
    no: str = Field(description="题号")
    question_text: str | None = Field(None, description="题目文本")
    student_answer: str | None = Field(None, description="学生答案")
    question_type: str | None = Field(None, description="题目类型")
    create_time: str | None = Field(None, description="创建时间")
    blocks: list[BlockInfo] = Field(default_factory=list, description="题目区域裁切块列表")
    correction: CorrectionInfo | None = Field(None, description="批改结果，未批改时为 null")
    knowledge_refs: list[KnowledgeRef] = Field(default_factory=list, description="关联知识库引用列表")

    model_config = {
        "json_schema_extra": {
            "example": {
                "no": "1",
                "question_text": "小明有12个苹果，吃了3个，又买了5个，现在有多少个苹果？",
                "student_answer": "14个",
                "question_type": "应用题",
                "create_time": "2026-06-04T10:01:00",
                "blocks": [
                    {
                        "url": "https://minio.example.com/homework/1/1717488000_math_homework.jpg",
                        "x1": 0.12,
                        "y1": 0.08,
                        "x2": 0.65,
                        "y2": 0.35,
                    }
                ],
                "correction": {
                    "score": 10.0,
                    "result": "correct",
                    "comment": "回答正确，计算过程无误",
                    "analysis": "12-3+5=14，先减后加，运算顺序正确",
                },
                "knowledge_refs": [
                    {
                        "knowledge_id": 1,
                        "title": "二年级数学知识点汇总.pdf",
                        "content": "加减混合运算：在没有括号的算式里，只有加减法，要从左往右按顺序计算。",
                        "score": 0.95,
                    }
                ],
            }
        }
    }


class ImageInfo(BaseModel):
    url: str = Field(description="作业图片访问地址")

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://minio.example.com/homework/1/1717488000_math_homework.jpg",
            }
        }
    }


class HomeworkResult(BaseModel):
    task_id: str = Field(description="任务唯一标识")
    status: str = Field(description="任务状态")
    subject: str | None = Field(None, description="科目")
    grade: str | None = Field(None, description="年级")
    mode: str | None = Field(None, description="批改模式")
    create_time: str | None = Field(None, description="创建时间")
    images: list[ImageInfo] = Field(default_factory=list, description="作业原始图片列表")
    questions: list[QuestionResult] = Field(default_factory=list, description="识别出的题目及批改结果列表")

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "completed",
                "subject": "数学",
                "grade": "二年级",
                "mode": "aliyun",
                "create_time": "2026-06-04T10:00:00",
                "images": [
                    {"url": "https://minio.example.com/homework/1/1717488000_math_homework.jpg"}
                ],
                "questions": [
                    {
                        "no": "1",
                        "question_text": "小明有12个苹果，吃了3个，又买了5个，现在有多少个苹果？",
                        "student_answer": "14个",
                        "question_type": "应用题",
                        "create_time": "2026-06-04T10:01:00",
                        "blocks": [
                            {
                                "url": "https://minio.example.com/homework/1/1717488000_math_homework.jpg",
                                "x1": 0.12, "y1": 0.08, "x2": 0.65, "y2": 0.35,
                            }
                        ],
                        "correction": {
                            "score": 10.0,
                            "result": "correct",
                            "comment": "回答正确，计算过程无误",
                            "analysis": "12-3+5=14，先减后加，运算顺序正确",
                        },
                        "knowledge_refs": [
                            {
                                "knowledge_id": 1,
                                "title": "二年级数学知识点汇总.pdf",
                                "content": "加减混合运算：在没有括号的算式里，只有加减法，要从左往右按顺序计算。",
                                "score": 0.95,
                            }
                        ],
                    }
                ],
            }
        }
    }